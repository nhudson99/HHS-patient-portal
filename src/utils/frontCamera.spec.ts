import { describe, expect, it, vi } from 'vitest'
import {
  acquireFrontCameraStream,
  classifyGetUserMediaError,
  frontCameraConstraintAttempts,
  FrontCameraError,
  isRearFacingStream,
  isSecureCameraContext,
  trackFacingMode,
} from './frontCamera'

function mockStream(facingMode?: string): MediaStream {
  const track = {
    readyState: 'live',
    stop: vi.fn(),
    getSettings: () => (facingMode ? { facingMode } : {}),
  }
  return {
    getVideoTracks: () => [track],
    getTracks: () => [track],
  } as unknown as MediaStream
}

describe('frontCamera helpers', () => {
  it('requires a secure context with getUserMedia', () => {
    expect(isSecureCameraContext(false, { getUserMedia: vi.fn() })).toBe(false)
    expect(isSecureCameraContext(true, null)).toBe(false)
    expect(isSecureCameraContext(true, { getUserMedia: vi.fn() })).toBe(true)
  })

  it('detects rear-facing streams from track settings', () => {
    expect(trackFacingMode(mockStream('user'))).toBe('user')
    expect(isRearFacingStream(mockStream('environment'))).toBe(true)
    expect(isRearFacingStream(mockStream('user'))).toBe(false)
    expect(isRearFacingStream(mockStream())).toBe(false)
  })

  it('tries exact user, ideal user, then any video', () => {
    const attempts = frontCameraConstraintAttempts()
    expect(attempts).toHaveLength(3)
    expect(attempts[0]).toEqual({ video: { facingMode: { exact: 'user' } }, audio: false })
    expect(attempts[1]).toEqual({ video: { facingMode: { ideal: 'user' } }, audio: false })
    expect(attempts[2]).toEqual({ video: true, audio: false })
  })

  it('classifies permission errors', () => {
    expect(classifyGetUserMediaError({ name: 'NotAllowedError' })).toBe('permission')
    expect(classifyGetUserMediaError({ name: 'OverconstrainedError' })).toBe('unavailable')
  })

  it('returns the first non-rear stream', async () => {
    const front = mockStream('user')
    const getUserMedia = vi
      .fn()
      .mockRejectedValueOnce({ name: 'OverconstrainedError' })
      .mockResolvedValueOnce(front)

    const stream = await acquireFrontCameraStream(
      { getUserMedia } as unknown as MediaDevices,
      { isSecureContext: true },
    )
    expect(stream).toBe(front)
    expect(getUserMedia).toHaveBeenCalledTimes(2)
  })

  it('stops rear streams and keeps looking', async () => {
    const rear = mockStream('environment')
    const front = mockStream('user')
    const getUserMedia = vi
      .fn()
      .mockResolvedValueOnce(rear)
      .mockResolvedValueOnce(front)

    const stream = await acquireFrontCameraStream(
      { getUserMedia } as unknown as MediaDevices,
      { isSecureContext: true },
    )
    expect(stream).toBe(front)
    expect(rear.getTracks()[0].stop).toHaveBeenCalled()
  })

  it('rejects when only a rear camera is available', async () => {
    const getUserMedia = vi.fn().mockResolvedValue(mockStream('environment'))

    await expect(
      acquireFrontCameraStream(
        { getUserMedia } as unknown as MediaDevices,
        { isSecureContext: true },
      ),
    ).rejects.toMatchObject({ reason: 'rear_only' } satisfies Partial<FrontCameraError>)
  })

  it('rejects insecure contexts before calling getUserMedia', async () => {
    const getUserMedia = vi.fn()
    await expect(
      acquireFrontCameraStream(
        { getUserMedia } as unknown as MediaDevices,
        { isSecureContext: false },
      ),
    ).rejects.toMatchObject({ reason: 'insecure' })
    expect(getUserMedia).not.toHaveBeenCalled()
  })
})
