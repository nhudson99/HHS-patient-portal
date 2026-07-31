/**
 * Helpers for opening the user-facing (front) camera on kiosk tablets.
 * Prefer facingMode "user"; never keep an environment/rear stream.
 */

export type FrontCameraFailureReason =
  | 'unsupported'
  | 'insecure'
  | 'permission'
  | 'unavailable'
  | 'rear_only'

export class FrontCameraError extends Error {
  reason: FrontCameraFailureReason

  constructor(reason: FrontCameraFailureReason, message: string) {
    super(message)
    this.name = 'FrontCameraError'
    this.reason = reason
  }
}

export function isSecureCameraContext(
  isSecureContext: boolean,
  mediaDevices: Pick<MediaDevices, 'getUserMedia'> | null | undefined,
): boolean {
  return Boolean(isSecureContext && mediaDevices?.getUserMedia)
}

export function trackFacingMode(stream: MediaStream): string | undefined {
  const track = stream.getVideoTracks()[0]
  if (!track) return undefined
  const settings = track.getSettings?.() ?? {}
  return typeof settings.facingMode === 'string' ? settings.facingMode : undefined
}

/** True when the stream is known to be a rear / world-facing camera. */
export function isRearFacingStream(stream: MediaStream): boolean {
  return trackFacingMode(stream) === 'environment'
}

export function frontCameraConstraintAttempts(): MediaStreamConstraints[] {
  return [
    { video: { facingMode: { exact: 'user' } }, audio: false },
    { video: { facingMode: { ideal: 'user' } }, audio: false },
    // Some desktop / kiosk WebViews reject facingMode entirely. Open any
    // camera, then reject the stream if settings report environment.
    { video: true, audio: false },
  ]
}

export function classifyGetUserMediaError(err: unknown): FrontCameraFailureReason {
  const name = err && typeof err === 'object' && 'name' in err ? String((err as { name: string }).name) : ''
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError' || name === 'SecurityError') {
    return 'permission'
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return 'unavailable'
  }
  if (name === 'OverconstrainedError' || name === 'ConstraintNotSatisfiedError') {
    return 'unavailable'
  }
  return 'unavailable'
}

export function frontCameraErrorMessage(reason: FrontCameraFailureReason): string {
  switch (reason) {
    case 'insecure':
      return 'Camera requires a secure connection (HTTPS or localhost).'
    case 'unsupported':
      return 'Camera is not supported in this browser.'
    case 'permission':
      return 'Camera permission was denied. Tap Enable Camera to try again, or skip.'
    case 'rear_only':
      return 'Front camera is not available on this device.'
    default:
      return 'Unable to open the front camera. Tap Enable Camera to try again, or skip.'
  }
}

/**
 * Acquire a front-facing MediaStream. Stops and discards rear-camera streams.
 * Call during a user gesture when possible (iOS / Safari kiosk browsers).
 */
export async function acquireFrontCameraStream(
  mediaDevices: MediaDevices,
  options: { isSecureContext: boolean } = { isSecureContext: true },
): Promise<MediaStream> {
  if (!options.isSecureContext) {
    throw new FrontCameraError('insecure', frontCameraErrorMessage('insecure'))
  }
  if (!mediaDevices?.getUserMedia) {
    throw new FrontCameraError('unsupported', frontCameraErrorMessage('unsupported'))
  }

  let lastReason: FrontCameraFailureReason = 'unavailable'
  let sawRearOnly = false

  for (const constraints of frontCameraConstraintAttempts()) {
    try {
      const stream = await mediaDevices.getUserMedia(constraints)
      if (isRearFacingStream(stream)) {
        for (const track of stream.getTracks()) track.stop()
        sawRearOnly = true
        lastReason = 'rear_only'
        continue
      }
      return stream
    } catch (err) {
      lastReason = classifyGetUserMediaError(err)
    }
  }

  if (sawRearOnly && lastReason === 'rear_only') {
    throw new FrontCameraError('rear_only', frontCameraErrorMessage('rear_only'))
  }
  throw new FrontCameraError(lastReason, frontCameraErrorMessage(lastReason))
}
