import { useState, useEffect, useRef, useCallback } from 'react'
import { Phone, PhoneOff, Mic, MicOff, Video, VideoOff, Monitor, MonitorOff, UserPlus, X, Radio, Users } from 'lucide-react'
import { useCallStore } from '../store/callStore'
import { useWebSocketStore } from '../store/websocketStore'
import { useAuthStore } from '../store/authStore'
import api from '../api/axios'
import toast from 'react-hot-toast'
import Avatar from './Avatar'

const ICE_SERVERS = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
  { urls: 'stun:stun2.l.google.com:19302' },
]

export default function CallModal() {
  const {
    activeCall, incomingCall, callStatus,
    isMuted, isCameraOff, isScreenSharing,
    localStream, remoteStreams, peerConnections,
    setActiveCall, setIncomingCall, setCallStatus,
    toggleMute, toggleCamera, setScreenSharing,
    setLocalStream, addRemoteStream, removeRemoteStream,
    addPeerConnection, cleanup
  } = useCallStore()

  const { ws } = useWebSocketStore()
  const { user } = useAuthStore()
  const localVideoRef = useRef(null)
  const remoteVideoRefs = useRef({})
  const [callDuration, setCallDuration] = useState(0)
  const durationInterval = useRef(null)

  // Start duration timer when active
  useEffect(() => {
    if (callStatus === 'active') {
      setCallDuration(0)
      durationInterval.current = setInterval(() => setCallDuration(d => d + 1), 1000)
    } else {
      if (durationInterval.current) clearInterval(durationInterval.current)
    }
    return () => { if (durationInterval.current) clearInterval(durationInterval.current) }
  }, [callStatus])

  // Assign local stream to video element
  useEffect(() => {
    if (localVideoRef.current && localStream) {
      localVideoRef.current.srcObject = localStream
    }
  }, [localStream])

  // Assign remote streams
  useEffect(() => {
    Object.entries(remoteStreams).forEach(([peerId, stream]) => {
      const el = remoteVideoRefs.current[peerId]
      if (el) {
        el.srcObject = stream
        console.log('Assigned stream to video element for', peerId, 'video tracks:', stream.getVideoTracks().length, 'audio tracks:', stream.getAudioTracks().length)
        // Force video element to reload
        el.load()
      }
    })
  }, [remoteStreams])

  const createPeerConnection = useCallback((peerId) => {
    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS })

    pc.onicecandidate = (event) => {
      if (event.candidate && ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'call_signal',
          call_id: useCallStore.getState().activeCall?.id,
          signal_type: 'ice-candidate',
          signal: event.candidate,
          recipients: [peerId],
        }))
      }
    }

    pc.ontrack = (event) => {
      console.log('ontrack fired for', peerId, 'streams:', event.streams.length, 'track:', event.track.kind, 'enabled:', event.track.enabled, 'muted:', event.track.muted)
      const stream = event.streams[0]
      // Unmute video track if it's muted
      if (event.track.kind === 'video' && event.track.muted) {
        event.track.enabled = true
        console.log('Unmuted video track for', peerId)
      }
      addRemoteStream(peerId, stream)
      // Force video element update immediately
      const el = remoteVideoRefs.current[peerId]
      if (el) {
        el.srcObject = stream
        console.log('Updated video element for', peerId, 'with new stream, tracks:', stream.getTracks().length)
        // Force play
        el.play().catch(e => console.log('Play error:', e))
      }
    }

    pc.onconnectionstatechange = () => {
      if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
        removeRemoteStream(peerId)
      }
    }

    // Add local tracks
    if (localStream) {
      localStream.getTracks().forEach(track => pc.addTrack(track, localStream))
    }

    addPeerConnection(peerId, pc)
    return pc
  }, [ws, activeCall, localStream, addRemoteStream, removeRemoteStream, addPeerConnection])

  // Handle incoming WebRTC signals
  const handleSignal = useCallback(async (data) => {
    const { signal_type, signal, from_user, call_id } = data

    // Read fresh state to avoid stale-closure races (offer arriving before re-render)
    const state = useCallStore.getState()
    const currentCall = state.activeCall
    if (call_id !== currentCall?.id) {
      console.warn('Ignoring signal for non-active call', call_id, 'active:', currentCall?.id)
      return
    }

    let pc = state.peerConnections[from_user]
    if (!pc) {
      pc = createPeerConnection(from_user)
    }

    if (signal_type === 'offer') {
      console.log('Received offer from', from_user, 'signalingState:', pc.signalingState)
      await pc.setRemoteDescription(new RTCSessionDescription(signal))
      const answer = await pc.createAnswer()
      await pc.setLocalDescription(answer)
      ws?.send(JSON.stringify({
        type: 'call_signal',
        call_id,
        signal_type: 'answer',
        signal: answer,
        recipients: [from_user],
      }))
      console.log('Sent answer to', from_user)
    } else if (signal_type === 'answer') {
      console.log('Received answer from', from_user)
      await pc.setRemoteDescription(new RTCSessionDescription(signal))
    } else if (signal_type === 'ice-candidate') {
      try {
        await pc.addIceCandidate(new RTCIceCandidate(signal))
      } catch (e) { /* ignore */ }
    }
  }, [activeCall, peerConnections, createPeerConnection, ws])

  // Start outgoing call
  const startCall = useCallback(async (callType, participantIds, callId, isBroadcast = false, chatId = null) => {
    try {
      // Fetch participant info
      const participantsInfo = await Promise.all(
        participantIds.map(async (id) => {
          try {
            const res = await api.get(`/auth/users/${id}`)
            return {
              user_id: id,
              first_name: res.data.first_name,
              last_name: res.data.last_name,
              avatar_url: res.data.avatar_url,
            }
          } catch (e) {
            return { user_id: id, first_name: 'Unknown', last_name: '', avatar_url: null }
          }
        })
      )

      const constraints = { audio: true, video: callType === 'video' }
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      setLocalStream(stream)
      
      // Для трансляций сразу active, для обычных звонков - ringing
      const initialStatus = isBroadcast ? 'active' : 'ringing'
      setCallStatus(initialStatus)
      setActiveCall({ id: callId, type: callType, participants: participantsInfo, isOutgoing: true, isBroadcast })

      // Send invite via WS (только для обычных звонков)
      if (!isBroadcast) {
        ws?.send(JSON.stringify({
          type: 'call_invite',
          call_id: callId,
          call_type: callType,
          from_name: `${user?.first_name} ${user?.last_name}`,
          from_avatar: user?.avatar_url,
          recipients: participantIds,
        }))

        // Timeout if no answer
        setTimeout(() => {
          const state = useCallStore.getState()
          if (state.callStatus === 'ringing') {
            endCall()
            toast.error('Нет ответа')
          }
        }, 30000)
      } else {
        // Для трансляций уведомляем всех участников канала
        ws?.send(JSON.stringify({
          type: 'broadcast_started',
          call_id: callId,
          call_type: callType,
          from_name: `${user?.first_name} ${user?.last_name}`,
          from_avatar: user?.avatar_url,
          chat_id: chatId,
        }))
      }
    } catch (err) {
      console.error('Media access error:', err.name, err.message, err)
      let errorMsg = 'Нет доступа к микрофону/камере'
      if (err.name === 'NotAllowedError') {
        errorMsg = 'Разрешите доступ к камере и микрофону в браузере'
      } else if (err.name === 'NotFoundError') {
        errorMsg = 'Камера или микрофон не найдены'
      } else if (err.name === 'NotReadableError') {
        errorMsg = 'Камера или микрофон заняты другим приложением'
      } else if (err.name === 'OverconstrainedError') {
        errorMsg = 'Устройство не поддерживает запрошенные параметры'
      }
      toast.error(errorMsg)
      cleanup()
    }
  }, [ws, user, setLocalStream, setCallStatus, setActiveCall, cleanup])

  // Accept incoming call
  const acceptCall = useCallback(async () => {
    if (!incomingCall) return
    try {
      // Fetch caller info
      let callerInfo
      try {
        const res = await api.get(`/auth/users/${incomingCall.from_user}`)
        callerInfo = {
          user_id: incomingCall.from_user,
          first_name: res.data.first_name,
          last_name: res.data.last_name,
          avatar_url: res.data.avatar_url,
        }
      } catch (e) {
        callerInfo = {
          user_id: incomingCall.from_user,
          first_name: incomingCall.from_name || 'Unknown',
          last_name: '',
          avatar_url: incomingCall.from_avatar || null,
        }
      }

      const constraints = { audio: true, video: incomingCall.call_type === 'video' }
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      setLocalStream(stream)
      setActiveCall({
        id: incomingCall.call_id,
        type: incomingCall.call_type,
        participants: [callerInfo],
        isOutgoing: false
      })
      setCallStatus('connecting')
      setIncomingCall(null)

      // Notify caller we accepted; the caller will create the offer
      ws?.send(JSON.stringify({
        type: 'call_accept',
        call_id: incomingCall.call_id,
        recipients: [incomingCall.from_user],
      }))

      // Join call in backend
      try { await api.post(`/calls/${incomingCall.call_id}/join`) } catch (e) { /* ignore */ }

      // Pre-create peer connection so handleSignal finds it on offer arrival
      createPeerConnection(incomingCall.from_user)
      setCallStatus('active')
    } catch (err) {
      console.error('Media access error (accept):', err.name, err.message, err)
      let errorMsg = 'Нет доступа к микрофону/камере'
      if (err.name === 'NotAllowedError') {
        errorMsg = 'Разрешите доступ к камере и микрофону в браузере'
      } else if (err.name === 'NotFoundError') {
        errorMsg = 'Камера или микрофон не найдены'
      } else if (err.name === 'NotReadableError') {
        errorMsg = 'Камера или микрофон заняты другим приложением'
      } else if (err.name === 'OverconstrainedError') {
        errorMsg = 'Устройство не поддерживает запрошенные параметры'
      }
      toast.error(errorMsg)
      rejectCall()
    }
  }, [incomingCall, ws, setLocalStream, setActiveCall, setCallStatus, setIncomingCall, createPeerConnection])

  // Reject incoming call
  const rejectCall = useCallback(() => {
    if (!incomingCall) return
    ws?.send(JSON.stringify({
      type: 'call_reject',
      call_id: incomingCall.call_id,
      recipients: [incomingCall.from_user],
    }))
    setIncomingCall(null)
  }, [incomingCall, ws, setIncomingCall])

  // End active call
  const endCall = useCallback(async () => {
    if (activeCall) {
      // Validate call_id before making API calls
      if (!activeCall.id || activeCall.id === 'undefined') {
        console.error('Invalid call_id in endCall:', activeCall.id)
        cleanup()
        return
      }

      const participants = activeCall.participants || []
      const recipients = participants.map(p => p.user_id).filter(Boolean)

      if (activeCall.isBroadcast) {
        if (activeCall.isOutgoing) {
          // Ведущий завершает трансляцию для всех
          ws?.send(JSON.stringify({
            type: 'call_end',
            call_id: activeCall.id,
            recipients,
          }))
          try { await api.post(`/calls/${activeCall.id}/end`) } catch (e) { /* ok */ }
        } else {
          // Зритель просто покидает - трансляция продолжается
          ws?.send(JSON.stringify({
            type: 'call_leave',
            call_id: activeCall.id,
            from_user: user?.id,
            recipients,
          }))
          try { await api.post(`/calls/${activeCall.id}/leave`) } catch (e) { /* ok */ }
        }
      } else {
        // В обычном звонке (1-на-1) завершаем для всех участников
        ws?.send(JSON.stringify({
          type: 'call_end',
          call_id: activeCall.id,
          recipients,
        }))
        try { await api.post(`/calls/${activeCall.id}/end`) } catch (e) { /* ok */ }
      }
    }
    cleanup()
  }, [activeCall, ws, cleanup, user])

  // Handle call accepted by remote
  const handleCallAccepted = useCallback(async (data) => {
    if (data.call_id !== activeCall?.id) return
    setCallStatus('active')

    // Create offer to the peer who accepted
    const pc = createPeerConnection(data.from_user)
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    ws?.send(JSON.stringify({
      type: 'call_signal',
      call_id: data.call_id,
      signal_type: 'offer',
      signal: offer,
      recipients: [data.from_user],
    }))
  }, [activeCall, ws, setCallStatus, createPeerConnection])

  // Handle call ended by remote
  const handleCallEnded = useCallback(() => {
    cleanup()
    toast('Звонок завершён', { icon: '📞' })
  }, [cleanup])

  // Handle call rejected
  const handleCallRejected = useCallback(() => {
    cleanup()
    toast.error('Звонок отклонён')
  }, [cleanup])

  // Handle participant leaving call
  const handleCallLeave = useCallback((data) => {
    if (data.call_id !== activeCall?.id) return
    console.log('Participant left:', data.from_user)
    // Удаляем участника из списка
    setActiveCall(prev => {
      if (!prev) return prev
      return {
        ...prev,
        participants: prev.participants.filter(p => p.user_id !== data.from_user)
      }
    })
    // Удаляем peer connection и remote stream
    const { removeRemoteStream } = useCallStore.getState()
    removeRemoteStream(data.from_user)
    // Закрываем peer connection
    const pc = peerConnections[data.from_user]
    if (pc) {
      pc.close()
    }
    toast('Участник покинул звонок')
  }, [activeCall, peerConnections])

  // Handle broadcast join request - viewer asks for offer
  const handleBroadcastJoinRequest = useCallback(async (data) => {
    // Read fresh state to avoid stale-closure races
    const state = useCallStore.getState()
    const currentCall = state.activeCall
    if (data.call_id !== currentCall?.id || !currentCall?.isBroadcast) {
      console.warn('Ignoring broadcast_join_request', data.call_id, 'active:', currentCall?.id)
      return
    }
    console.log('Sending offer to viewer:', data.from_user)

    const currentLocalStream = state.localStream
    let pc = state.peerConnections[data.from_user]
    if (!pc) {
      // Create peer connection for this viewer
      pc = createPeerConnection(data.from_user)
    }
    // Add local tracks (broadcaster's video/audio) if not already added
    if (currentLocalStream && pc.getSenders().length === 0) {
      currentLocalStream.getTracks().forEach(track => pc.addTrack(track, currentLocalStream))
      console.log('Added local tracks to peer connection for viewer:', data.from_user)
    }
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    ws?.send(JSON.stringify({
      type: 'call_signal',
      call_id: data.call_id,
      signal_type: 'offer',
      signal: offer,
      recipients: [data.from_user],
    }))
  }, [createPeerConnection, ws])

  // Helper: set a video track on a peer connection (replace existing sender or add new), then renegotiate
  const setVideoTrackAndRenegotiate = useCallback(async (peerId, pc, videoTrack, stream) => {
    // Remove only the video sender
    const videoSender = pc.getSenders().find(s => s.track?.kind === 'video')
    if (videoSender) {
      pc.removeTrack(videoSender)
      console.log(`Removed video sender for ${peerId}`)
    }
    
    // Add the new video track
    pc.addTrack(videoTrack, stream)
    console.log(`Added new video track for ${peerId}`)
    
    try {
      const offer = await pc.createOffer({ 
        offerToReceiveAudio: true, 
        offerToReceiveVideo: true
      })
      await pc.setLocalDescription(offer)
      ws?.send(JSON.stringify({
        type: 'call_signal',
        call_id: activeCall?.id,
        signal_type: 'offer',
        signal: offer,
        recipients: [peerId],
      }))
      console.log(`Renegotiated with ${peerId}, sent offer`)
    } catch (e) {
      console.error(`Renegotiation error with ${peerId}:`, e)
    }
  }, [ws, activeCall])

  // Screen sharing
  const toggleScreenShare = useCallback(async () => {
    if (isScreenSharing) {
      try {
        // Switch back to camera
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true })
        setLocalStream(stream)
        setScreenSharing(false)
        const camVideoTrack = stream.getVideoTracks()[0]
        Object.entries(peerConnections).forEach(([peerId, pc]) => {
          if (camVideoTrack) setVideoTrackAndRenegotiate(peerId, pc, camVideoTrack, stream)
        })
      } catch (err) {
        console.error('Switch back to camera error:', err.name, err.message, err)
        toast.error('Не удалось переключиться на камеру')
      }
    } else {
      let screenStream
      try {
        console.log('Starting screen share...')
        screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true })
        const videoTrack = screenStream.getVideoTracks()[0]
        const audioTrack = screenStream.getAudioTracks()[0]
        console.log('Screen stream obtained:', videoTrack, 'enabled:', videoTrack.enabled, 'muted:', videoTrack.muted, audioTrack)

        videoTrack.onended = () => {
          console.log('Screen share ended by user')
          toggleScreenShare()
        }

        // Keep existing audio track from local stream (mic), add screen video track
        const existingAudioTracks = localStream?.getAudioTracks() || []
        const newStream = new MediaStream([...existingAudioTracks, videoTrack])
        setLocalStream(newStream)
        setScreenSharing(true)

        // Send screen video to all peers
        Object.entries(peerConnections).forEach(([peerId, pc]) => {
          setVideoTrackAndRenegotiate(peerId, pc, videoTrack, newStream)
        })
        toast.success('Демонстрация экрана начата')
      } catch (err) {
        console.error('Screen share error:', err.name, err.message, err)
        let errorMsg = 'Не удалось начать демонстрацию экрана'
        if (err.name === 'NotAllowedError') {
          errorMsg = 'Вы отменили выбор экрана'
        } else if (err.name === 'NotFoundError') {
          errorMsg = 'Нет доступных экранов'
        } else if (err.name === 'NotReadableError') {
          errorMsg = 'Экран занят другим приложением'
        }
        toast.error(errorMsg)
        // Stop screen stream if it was partially obtained
        if (screenStream) {
          screenStream.getTracks().forEach(t => t.stop())
        }
        return // Don't proceed with renegotiation on error
      }
    }
  }, [isScreenSharing, activeCall, localStream, peerConnections, setLocalStream, setScreenSharing])

  // Expose handlers for WebSocket events
  useEffect(() => {
    // Set up global call event handler
    window.__callHandlers = {
      handleSignal,
      handleCallAccepted,
      handleCallEnded,
      handleCallRejected,
      handleBroadcastJoinRequest,
      handleCallLeave,
    }
    return () => { delete window.__callHandlers }
  }, [handleSignal, handleCallAccepted, handleCallEnded, handleCallRejected, handleBroadcastJoinRequest, handleCallLeave])

  // Expose startCall globally so other components can use it
  useEffect(() => {
    window.__startCall = startCall
    return () => { delete window.__startCall }
  }, [startCall])

  const formatTime = (sec) => `${Math.floor(sec / 60).toString().padStart(2, '0')}:${(sec % 60).toString().padStart(2, '0')}`

  // Incoming call UI
  if (incomingCall) {
    return (
      <div className="fixed inset-0 z-[100] bg-black/70 flex items-center justify-center">
        <div className="bg-dark-900 border border-dark-700 rounded-3xl p-8 text-center shadow-2xl max-w-sm w-full animate-pulse-slow">
          <div className="w-20 h-20 rounded-full bg-dark-700 mx-auto mb-4 flex items-center justify-center overflow-hidden">
            {incomingCall.from_avatar ? (
              <img src={incomingCall.from_avatar} className="w-full h-full object-cover" />
            ) : (
              <span className="text-2xl text-white font-bold">{incomingCall.from_name?.[0] || '?'}</span>
            )}
          </div>
          <h3 className="text-white text-lg font-bold mb-1">{incomingCall.from_name || 'Неизвестный'}</h3>
          <p className="text-dark-400 text-sm mb-6">
            {incomingCall.call_type === 'video' ? 'Видеозвонок...' : 'Аудиозвонок...'}
          </p>
          <div className="flex items-center justify-center gap-6">
            <button onClick={rejectCall} className="w-14 h-14 rounded-full bg-red-600 hover:bg-red-700 flex items-center justify-center text-white transition-colors shadow-lg">
              <PhoneOff size={24} />
            </button>
            <button onClick={acceptCall} className="w-14 h-14 rounded-full bg-green-600 hover:bg-green-700 flex items-center justify-center text-white transition-colors shadow-lg">
              <Phone size={24} />
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Active call / ringing UI
  if (!activeCall) return null

  const isVideo = activeCall.type === 'video'
  const isBroadcast = activeCall.isBroadcast
  const isOutgoing = activeCall.isOutgoing
  const remoteStreamEntries = Object.entries(remoteStreams)

  return (
    <div className="fixed inset-0 z-[100] bg-dark-950 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4">
        <div>
          <h3 className="text-white font-bold text-sm">
            {isBroadcast ? 'Трансляция' : callStatus === 'ringing' ? 'Вызов...' : callStatus === 'connecting' ? 'Подключение...' : 'Звонок'}
          </h3>
          {callStatus === 'active' && (
            <span className="text-dark-400 text-xs">{formatTime(callDuration)}</span>
          )}
        </div>
        <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${isBroadcast ? 'bg-red-600/20 text-red-400' : isVideo ? 'bg-blue-600/20 text-blue-400' : 'bg-green-600/20 text-green-400'}`}>
          {isBroadcast ? 'Трансляция' : isVideo ? 'Видео' : 'Аудио'}
        </span>
      </div>

      {/* Video area */}
      <div className="flex-1 relative flex items-center justify-center bg-dark-950 overflow-hidden pb-20">
        {/* Broadcast mode: show broadcaster on main screen */}
        {isBroadcast ? (
          <>
            {/* Если я ведущий - показываю свой stream на большом экране */}
            {isOutgoing && localStream && isVideo ? (
              <div className="w-full h-full absolute inset-0">
                <video ref={localVideoRef} autoPlay muted playsInline className="w-full h-full object-cover" />
                <div className="absolute bottom-4 left-4 flex items-center gap-2 z-10">
                  <Avatar 
                    name={`${user?.first_name} ${user?.last_name}`} 
                    url={user?.avatar_url} 
                    size="md" 
                  />
                  <span className="text-white text-sm font-medium bg-black/50 px-3 py-1.5 rounded">
                    Вы (ведущий)
                  </span>
                </div>
              </div>
            ) : (
              /* Если я зритель - показываю stream ведущего */
              remoteStreamEntries.length > 0 ? (
                <div className="w-full h-full absolute inset-0">
                  {remoteStreamEntries.map(([peerId, stream]) => {
                    const participant = activeCall?.participants?.find(p => p.user_id === peerId)
                    const participantName = participant ? `${participant.first_name} ${participant.last_name}` : 'Ведущий'
                    return (
                      <div key={peerId} className="w-full h-full relative">
                        <video
                          ref={el => { if (el) remoteVideoRefs.current[peerId] = el }}
                          autoPlay
                          playsInline
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute bottom-4 left-4 flex items-center gap-2 z-10">
                          <Avatar 
                            name={participantName} 
                            url={participant?.avatar_url} 
                            size="md" 
                          />
                          <span className="text-white text-sm font-medium bg-black/50 px-3 py-1.5 rounded">
                            {participantName}
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="text-center">
                  <div className="w-24 h-24 rounded-full bg-dark-800 mx-auto mb-4 flex items-center justify-center">
                    <Radio size={36} className="text-red-400 animate-pulse" />
                  </div>
                  <p className="text-dark-400 text-sm">Ожидание трансляции...</p>
                </div>
              )
            )}
            
            {/* Local video for viewers (picture-in-picture) */}
            {!isOutgoing && localStream && isVideo && (
              <div className="absolute bottom-4 right-4 w-40 h-28 rounded-xl overflow-hidden border-2 border-dark-600 shadow-xl bg-dark-900 z-10">
                <video ref={localVideoRef} autoPlay muted playsInline className="w-full h-full object-cover" />
                <div className="absolute bottom-2 left-2 flex items-center gap-2">
                  <Avatar 
                    name={`${user?.first_name} ${user?.last_name}`} 
                    url={user?.avatar_url} 
                    size="sm" 
                  />
                  <span className="text-white text-xs font-medium bg-black/50 px-2 py-1 rounded">
                    Вы
                  </span>
                </div>
              </div>
            )}
          </>
        ) : (
          /* Regular call mode */
          <>
            {/* Remote streams */}
            {remoteStreamEntries.length > 0 ? (
              <div className={`grid gap-2 w-full h-full p-4 ${remoteStreamEntries.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
                {remoteStreamEntries.map(([peerId, stream]) => {
                  const participant = activeCall?.participants?.find(p => p.user_id === peerId)
                  const participantName = participant ? `${participant.first_name} ${participant.last_name}` : 'Участник'
                  const hasVideo = stream.getVideoTracks().length > 0
                  return (
                    <div key={peerId} className="relative rounded-2xl overflow-hidden bg-dark-800">
                      {hasVideo ? (
                        <video
                          ref={el => { if (el) remoteVideoRefs.current[peerId] = el }}
                          autoPlay
                          playsInline
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-dark-800">
                          <Avatar 
                            name={participantName} 
                            url={participant?.avatar_url} 
                            size="lg" 
                          />
                        </div>
                      )}
                      {/* Avatar overlay (only if video is present) */}
                      {hasVideo && (
                        <div className="absolute bottom-3 left-3 flex items-center gap-2">
                          <Avatar 
                            name={participantName} 
                            url={participant?.avatar_url} 
                            size="sm" 
                          />
                          <span className="text-white text-xs font-medium bg-black/50 px-2 py-1 rounded">
                            {participantName}
                          </span>
                        </div>
                      )}
                      {/* Name label (only if no video) */}
                      {!hasVideo && (
                        <div className="absolute bottom-4 left-0 right-0 text-center">
                          <span className="text-white text-sm font-medium bg-black/50 px-3 py-1.5 rounded inline-block">
                            {participantName}
                          </span>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center">
                {activeCall?.participants?.length > 0 ? (
                  <div className="flex flex-col items-center">
                    {activeCall.participants.map(p => (
                      <div key={p.user_id} className="mb-4">
                        <Avatar 
                          name={`${p.first_name} ${p.last_name}`} 
                          url={p.avatar_url} 
                          size="lg" 
                        />
                        <p className="text-white text-sm mt-2">{p.first_name} {p.last_name}</p>
                      </div>
                    ))}
                    <p className="text-dark-400 text-sm">
                      {callStatus === 'ringing' ? 'Ожидание ответа...' : callStatus === 'connecting' ? 'Подключение...' : 'Звонок активен'}
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="w-24 h-24 rounded-full bg-dark-800 mx-auto mb-4 flex items-center justify-center">
                      <Phone size={36} className={`text-dark-400 ${callStatus === 'ringing' ? 'animate-bounce' : ''}`} />
                    </div>
                    <p className="text-dark-400 text-sm">
                      {callStatus === 'ringing' ? 'Ожидание ответа...' : callStatus === 'connecting' ? 'Подключение...' : 'Звонок активен'}
                    </p>
                  </>
                )}
              </div>
            )}

            {/* Local video (picture-in-picture) */}
            {localStream && (isVideo || isScreenSharing) && (
              <div className="absolute bottom-4 right-4 w-40 h-28 rounded-xl overflow-hidden border-2 border-dark-600 shadow-xl bg-dark-900">
                <video ref={localVideoRef} autoPlay muted playsInline className="w-full h-full object-cover" />
                <div className="absolute bottom-2 left-2 flex items-center gap-2">
                  <Avatar 
                    name={`${user?.first_name} ${user?.last_name}`} 
                    url={user?.avatar_url} 
                    size="sm" 
                  />
                  <span className="text-white text-xs font-medium bg-black/50 px-2 py-1 rounded">
                    Вы
                  </span>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Controls */}
      <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-6 py-4 bg-dark-900/90 border-t border-dark-800 z-20">
        {/* Left side: viewer count for broadcasts */}
        {isBroadcast && (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-dark-800 rounded-lg">
              <Users size={16} className="text-dark-400" />
              <span className="text-white text-sm font-medium">
                {remoteStreamEntries.length} зритель{remoteStreamEntries.length !== 1 ? (remoteStreamEntries.length > 4 ? 'ей' : 'я') : ''}
              </span>
            </div>
          </div>
        )}

        {/* Center: main controls */}
        <div className="flex items-center justify-center gap-4">
          {/* Only show controls for broadcaster or regular calls */}
          {!isBroadcast || isOutgoing ? (
            <>
              <button onClick={toggleMute}
                className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${isMuted ? 'bg-red-600 text-white' : 'bg-dark-700 text-white hover:bg-dark-600'}`}
                title={isMuted ? 'Включить микрофон' : 'Выключить микрофон'}>
                {isMuted ? <MicOff size={20} /> : <Mic size={20} />}
              </button>

              {isVideo && (
                <button onClick={toggleCamera}
                  className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${isCameraOff ? 'bg-red-600 text-white' : 'bg-dark-700 text-white hover:bg-dark-600'}`}
                  title={isCameraOff ? 'Включить камеру' : 'Выключить камеру'}>
                  {isCameraOff ? <VideoOff size={20} /> : <Video size={20} />}
                </button>
              )}

              <button onClick={toggleScreenShare}
                className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${isScreenSharing ? 'bg-blue-600 text-white' : 'bg-dark-700 text-white hover:bg-dark-600'}`}
                title={isScreenSharing ? 'Остановить демонстрацию' : 'Демонстрация экрана'}>
                {isScreenSharing ? <MonitorOff size={20} /> : <Monitor size={20} />}
              </button>
            </>
          ) : null}

          <button onClick={endCall}
            className={`w-14 h-14 rounded-full flex items-center justify-center text-white transition-colors shadow-lg ${isBroadcast && isOutgoing ? 'bg-red-600 hover:bg-red-700' : 'bg-red-600 hover:bg-red-700'}`}
            title={isBroadcast && isOutgoing ? 'Завершить трансляцию' : isBroadcast ? 'Выйти из трансляции' : 'Завершить звонок'}>
            <PhoneOff size={22} />
          </button>
        </div>

        {/* Right side: spacer for balance */}
        {isBroadcast && <div className="w-32" />}
      </div>
    </div>
  )
}
