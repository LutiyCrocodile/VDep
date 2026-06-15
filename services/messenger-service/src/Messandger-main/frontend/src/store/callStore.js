import { create } from 'zustand'

export const useCallStore = create((set, get) => ({
  // Call state
  activeCall: null, // { id, type: 'audio'|'video', participants: [{user_id, first_name, last_name, avatar_url}], isOutgoing: bool, isBroadcast: bool }
  incomingCall: null, // { call_id, call_type, from_user, from_name, from_avatar }
  callStatus: 'idle', // idle, ringing, connecting, active, ended
  broadcastInfo: null, // { call_id, call_type, from_user, from_name, from_avatar }

  // Media state
  isMuted: false,
  isCameraOff: false,
  isScreenSharing: false,

  // WebRTC
  localStream: null,
  remoteStreams: {}, // { peerId: MediaStream }
  peerConnections: {}, // { peerId: RTCPeerConnection }

  // Actions
  setActiveCall: (call) => set({ activeCall: call }),
  setIncomingCall: (call) => set({ incomingCall: call }),
  setCallStatus: (status) => set({ callStatus: status }),
  setBroadcastInfo: (info) => set({ broadcastInfo: info }),

  toggleMute: () => {
    const { localStream, isMuted } = get()
    if (localStream) {
      localStream.getAudioTracks().forEach(t => { t.enabled = isMuted })
    }
    set({ isMuted: !isMuted })
  },

  toggleCamera: () => {
    const { localStream, isCameraOff } = get()
    if (localStream) {
      localStream.getVideoTracks().forEach(t => { t.enabled = isCameraOff })
    }
    set({ isCameraOff: !isCameraOff })
  },

  setScreenSharing: (sharing) => set({ isScreenSharing: sharing }),
  setLocalStream: (stream) => set({ localStream: stream }),

  addRemoteStream: (peerId, stream) => set(s => ({
    remoteStreams: { ...s.remoteStreams, [peerId]: stream }
  })),

  removeRemoteStream: (peerId) => set(s => {
    const { [peerId]: _, ...rest } = s.remoteStreams
    return { remoteStreams: rest }
  }),

  addPeerConnection: (peerId, pc) => set(s => ({
    peerConnections: { ...s.peerConnections, [peerId]: pc }
  })),

  cleanup: () => {
    const { localStream, peerConnections } = get()
    if (localStream) {
      localStream.getTracks().forEach(t => t.stop())
    }
    Object.values(peerConnections).forEach(pc => pc.close())
    set({
      activeCall: null,
      incomingCall: null,
      callStatus: 'idle',
      broadcastInfo: null,
      isMuted: false,
      isCameraOff: false,
      isScreenSharing: false,
      localStream: null,
      remoteStreams: {},
      peerConnections: {},
    })
  },
}))
