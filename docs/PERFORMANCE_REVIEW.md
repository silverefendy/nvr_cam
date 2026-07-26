# Performance Review

## Current Performance Model

The system is designed around efficient recording:

- Recording path uses FFmpeg stream copy by default, which is CPU-efficient.
- Live view uses HLS, with HEVC streams transcoded to H.264 for browser compatibility.
- Motion detection uses sub-stream frames and skips frames to reduce CPU load.
- Storage cleanup runs periodically and deletes old files when free space drops below threshold.
- Playback can remux H.264 or transcode HEVC on demand and cache the result.

This model is appropriate for a single-server NVR, but needs guardrails for 30 cameras and large playback files.

## High Priority Bottlenecks

| Priority | Bottleneck | Consequence | Recommendation | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| High | HEVC playback transcode happens synchronously in the request path. | First playback of large files can take minutes and hold server resources. | Move to background jobs with progress/status and queue limits. | Medium | High | 2-3 days |
| High | HLS transcode may run per HEVC camera. | Many HEVC live streams can overload CPU. | Prefer camera sub-stream H.264 for live view; add max concurrent transcodes and CPU threshold fallback. | Medium | High | 1-2 days |
| High | Storage scanning uses recursive file walks per camera. | Large storage trees can slow cleanup and stats. | Use DB metadata for most stats; run filesystem reconciliation as scheduled maintenance. | Medium | High | 1-2 days |
| Medium | Motion detection loop uses blocking OpenCV capture. | Many cameras can starve event loop or slow detection. | Run detectors in separate processes/threads or dedicated service workers. | Medium | Medium | 2 days |

## Medium Priority Improvements

| Priority | Improvement | Why | Recommendation | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| Medium | Add `/tmp/nvr_remux` cache policy. | Remux/transcode cache can fill OS disk. | Size cap, age cap, cleanup loop, and metric in System page. | Low | Medium | 0.5 day |
| Medium | Add FFmpeg process limits. | Camera restarts and transcodes can spike CPU. | Central process supervisor with per-camera and global limits. | Medium | Medium | 1-2 days |
| Medium | Add DB indexes for common filters. | Playback/events pages depend on time and camera filters. | Verify composite indexes for `(camera_id, started_at desc)` and event severity/date filters. | Low | Medium | 0.5 day |
| Medium | Add API pagination. | `/recordings` returns up to 500 rows and may grow. | Cursor or date-based pagination with stable ordering. | Medium | Medium | 1 day |

## Performance Metrics to Track

- Active recording FFmpeg processes.
- Active HLS FFmpeg processes.
- Active transcode/remux jobs.
- CPU load and per-process CPU.
- Free disk percentage per drive.
- Recording write failures and 0-byte cleanup count.
- Playback preparation time by codec and file size.
- Motion detection frames processed per second.

## Recommended Safeguards

1. Refuse new playback transcodes when CPU is above a configured threshold.
2. Limit concurrent HEVC-to-H.264 playback jobs.
3. Prefer H.264 sub-streams for live view.
4. Use nightly or idle-time pre-processing for frequently accessed recordings.
5. Clean playback cache by size and age.
6. Keep recording stream copy as the default.

## Suggested Implementation Sketch

```text
recording selected
  -> API checks auth
  -> PlaybackService checks cache
  -> if cache missing, create playback_jobs row
  -> worker remuxes/transcodes with concurrency limits
  -> frontend polls /recordings/{id}/playback-status
  -> once ready, video src points to prepared cache URL
```

This keeps HTTP requests short and gives the user visible progress instead of a hanging video element.

