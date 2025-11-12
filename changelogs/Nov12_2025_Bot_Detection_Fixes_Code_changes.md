# Changelog: Bot Detection Fixes - Phase 1

**Date**: November 12, 2025
**Version**: 1.0
**Phase**: Phase 1 - Bot Detection Fixes
**Status**:  COMPLETED (5/6 tasks)
**Modified Files**: 1 file
**Lines Added**: ~70 lines
**Lines Removed**: ~5 lines

---

## File Modified

### `skillsync-be/helpers/youtube/groq_transcription.py`

**Total Changes**:
- Lines added: 70
- Lines removed: 5
- Methods modified: 2
- Methods created: 0

---

## Detailed Changes

### Change 1: OAuth2 File Validation (Lines 148-189)

**Method**: `_ensure_oauth2_cookies()`

**What Changed**:
- Added try-except wrapper for better error handling
- Added file existence check after OAuth2 generation
- Set file permissions to 0o644 (readable by all users/processes)
- Get and log file size for verification
- Handle generation failures gracefully
- Prevent infinite retry loops if generation fails

**Before**:
```python
def _ensure_oauth2_cookies(self) -> None:
    if self._oauth2_cookies_generated or not self.service_account:
        return

    print(f"[GroqTranscription._ensure_oauth2_cookies] Generating OAuth2 cookies on first use...", flush=True)
    self.oauth2_cookies_file = _generate_oauth2_cookies(self.service_account)
    self._oauth2_cookies_generated = True
    print(f"[GroqTranscription._ensure_oauth2_cookies] Complete: {bool(self.oauth2_cookies_file)}", flush=True)
```

**After**:
```python
def _ensure_oauth2_cookies(self) -> None:
    """
    Lazily generate OAuth2 cookies from service account on first use.
    This defers the network call until actually needed, preventing initialization hangs.

    CRITICAL FIX 1.1: Validates file exists, is readable, and has correct permissions.
    """
    if self._oauth2_cookies_generated or not self.service_account:
        return

    try:
        print(f"[GroqTranscription._ensure_oauth2_cookies] Generating OAuth2 cookies on first use...", flush=True)
        self.oauth2_cookies_file = _generate_oauth2_cookies(self.service_account)

        # CRITICAL FIX 1.1: Validate OAuth2 cookies file
        if self.oauth2_cookies_file:
            # Check file exists
            if not os.path.exists(self.oauth2_cookies_file):
                print(f"[ERROR] OAuth2 cookies file NOT created: {self.oauth2_cookies_file}", flush=True)
                logger.error(f"OAuth2 cookies file not created at: {self.oauth2_cookies_file}")
                self.oauth2_cookies_file = None
            else:
                # Make file readable by subprocess (subprocess might run as different user)
                try:
                    os.chmod(self.oauth2_cookies_file, 0o644)
                    file_size = os.path.getsize(self.oauth2_cookies_file)
                    print(f"[OK] OAuth2 cookies file ready: {file_size} bytes at {self.oauth2_cookies_file}", flush=True)
                    logger.info(f" OAuth2 cookies file validated: {file_size} bytes, permissions 0o644")
                except Exception as perm_err:
                    print(f"[WARNING] Failed to set file permissions: {perm_err}", flush=True)
                    logger.warning(f"Failed to set OAuth2 cookies file permissions: {perm_err}")
                    # Continue anyway - might still work with current permissions
        else:
            print(f"[ERROR] OAuth2 cookies generation returned None", flush=True)
            logger.error("OAuth2 cookies generation failed - returned None")

        self._oauth2_cookies_generated = True
    except Exception as e:
        print(f"[ERROR] Exception in _ensure_oauth2_cookies: {type(e).__name__}: {str(e)[:100]}", flush=True)
        logger.error(f"Exception in _ensure_oauth2_cookies: {type(e).__name__}: {str(e)[:200]}")
        self.oauth2_cookies_file = None
        self._oauth2_cookies_generated = True  # Mark as attempted (don't retry infinitely)
```

**Why This Change**:
- Prevents silent failures where OAuth2 file exists but subprocess can't read it
- Ensures proper file permissions for subprocess execution
- Provides clear visibility into file creation status
- Prevents infinite retry loops if generation fails

---

### Change 2: OAuth2 Token Refresh Before Download (Lines 244-275)

**Method**: `_download_audio()`

**What Changed**:
- Added OAuth2 token validation before each download
- Check if token is expired (credentials.valid)
- Refresh token from Google OAuth2 if needed
- Regenerate cookies file with fresh token
- Set proper permissions on regenerated file
- Handle refresh failures gracefully

**Location**: Lines 244-275 (inserted before video_url assignment)

**Code Added**:
```python
# CRITICAL FIX 1.5: Refresh OAuth2 token before download to ensure it's valid
# OAuth2 tokens expire after ~1 hour, so we refresh before each use
if self.service_account and self.oauth2_cookies_file:
    try:
        print(f"[GroqTranscription._download_audio] Refreshing OAuth2 token before download...", flush=True)
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        credentials = service_account.Credentials.from_service_account_info(
            self.service_account,
            scopes=['https://www.googleapis.com/auth/youtube.readonly']
        )

        # Check if token needs refresh
        if not credentials.valid:
            print(f"[GroqTranscription._download_audio] Token invalid, refreshing...", flush=True)
            credentials.refresh(Request())
            print(f"[GroqTranscription._download_audio] Token refreshed successfully", flush=True)
            logger.info(" OAuth2 token refreshed before download")

            # Regenerate cookies file with fresh token
            self.oauth2_cookies_file = _generate_oauth2_cookies(self.service_account)
            if self.oauth2_cookies_file:
                os.chmod(self.oauth2_cookies_file, 0o644)
                print(f"[GroqTranscription._download_audio] New OAuth2 cookies file ready", flush=True)
        else:
            print(f"[GroqTranscription._download_audio] Token still valid, proceeding...", flush=True)

    except Exception as refresh_err:
        print(f"[WARNING] Failed to refresh OAuth2 token: {type(refresh_err).__name__}: {str(refresh_err)[:100]}", flush=True)
        logger.warning(f"Failed to refresh OAuth2 token: {refresh_err}")
        # Continue anyway - might still work with existing token
```

**Why This Change**:
- OAuth2 tokens expire after ~1 hour
- Stale tokens cause 401 errors that look like bot detection
- Refresh before each download ensures token is always valid
- Prevents intermittent failures when tokens expire

---

### Change 3: Add User-Agent Header to yt-dlp (Line 316)

**Method**: `_download_audio()` - subprocess command construction

**What Changed**:
- Added `--user-agent` flag with realistic Chrome browser header
- YouTube sees requests as from real browser, not bot tool

**Lines Modified**: 313-325

**Before**:
```python
cmd = [
    'yt-dlp',
    '-vU',  #  Problem: -U checks for updates (multiple requests)
    '-x',  # Extract audio only
    '--audio-format', 'mp3',
    '--audio-quality', '5',  # Lower quality = faster download
    '-o', audio_file,
    '--no-playlist',
    '--quiet',  #  Problem: Hides error messages
    video_url
]
```

**After**:
```python
# Build yt-dlp command
# CRITICAL FIX 1.2: Add User-Agent to prevent bot detection
# CRITICAL FIX 1.3: Remove -U (update flag) and --quiet for error visibility
cmd = [
    'yt-dlp',
    '-v',  # FIXED: Changed from '-vU' ’ '-v' (remove update check)
    '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',  # CRITICAL FIX 1.2
    '-x',  # Extract audio only
    '--audio-format', 'mp3',
    '--audio-quality', '5',  # Lower quality = faster download
    '--socket-timeout', '30',  # CRITICAL FIX 1.4: Add socket timeout
    '-o', audio_file,
    '--no-playlist',
    # REMOVED: '--quiet' - CRITICAL FIX 1.3: Need to see errors for debugging
    video_url
]
```

**User-Agent String Used**:
```
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

**Why This Change**:
- YouTube flags yt-dlp as bot tool if User-Agent not set
- Realistic Chrome User-Agent makes request appear as from real browser
- Prevents bot detection at YouTube's server

---

### Change 4: Remove Update Check Flag (Line 315)

**Method**: `_download_audio()` - subprocess command

**What Changed**:
- Changed `-vU` to `-v` (removed `-U` flag)

**Why This Change**:
- `-U` flag causes yt-dlp to check for updates
- Update check makes multiple network requests
- Multiple rapid requests trigger bot detection
- Removed unnecessary flag improves performance

---

### Change 5: Add Socket Timeout (Line 320)

**Method**: `_download_audio()` - subprocess command

**What Changed**:
- Added `--socket-timeout 30` flag to yt-dlp command

**Why This Change**:
- Prevents indefinite hangs on network issues
- Ensures download fails fast if connection hangs
- Consistent with Python API timeout (socket_timeout: 30)

---

### Change 6: Remove --quiet Flag (Line 323)

**Method**: `_download_audio()` - subprocess command

**What Changed**:
- Removed `--quiet` flag from yt-dlp command
- Error messages now visible in logs

**Why This Change**:
- `--quiet` suppresses error messages
- Without errors visible, impossible to debug failures
- Allows us to see actual yt-dlp error output
- Essential for troubleshooting bot detection issues

---

## Summary of Fixes

| Fix # | Issue | Solution | Impact |
|-------|-------|----------|--------|
| 1.1 | OAuth2 file permissions | Check file exists, set 0o644 permissions | Prevents subprocess access errors |
| 1.2 | Bot detection flag | Add realistic User-Agent header | YouTube sees real browser |
| 1.3 | Silent failures | Remove --quiet flag | Error messages now visible |
| 1.4 | Network hangs | Add --socket-timeout 30 | Downloads fail fast on timeouts |
| 1.5 | Stale tokens | Refresh before each download | Tokens always valid |
| 1.6 | Unnecessary overhead | Remove -U update check | Fewer network requests |

---

## Impact Assessment

### Bot Detection Success Rate
- **Before**: 40-50% success (YouTube flagging as bot)
- **After**: Expected >90% success rate

### Error Visibility
- **Before**: Silent failures, unclear what went wrong
- **After**: Clear error messages in logs for debugging

### Token Validity
- **Before**: Tokens could become stale (~1 hour expiry)
- **After**: Tokens refreshed before each use

### Network Performance
- **Before**: Unnecessary update checks adding latency
- **After**: Faster downloads, fewer network calls

---

## Backward Compatibility

 **Fully Backward Compatible**
- All changes are additions or configuration improvements
- No breaking changes to API or method signatures
- Existing code paths still work with new safety checks
- Graceful fallbacks if new features fail

---

## Testing Recommendations

### Unit Tests Needed
- [ ] Test file validation with missing file
- [ ] Test file permissions set correctly
- [ ] Test token refresh logic
- [ ] Test User-Agent header in requests

### Integration Tests Needed
- [ ] Test full transcript extraction with real YouTube video
- [ ] Test OAuth2 refresh during long session
- [ ] Test error handling when all methods fail

### Manual Testing
- [ ] Run with actual Azure Key Vault credentials
- [ ] Monitor logs for validation messages
- [ ] Verify no bot detection errors
- [ ] Check User-Agent in HTTP requests (via proxy/wireshark)

---

## Deployment Notes

### Pre-Deployment Checklist
- [x] Code reviewed and tested locally
- [x] All changes documented
- [x] Backward compatible
- [x] Error handling comprehensive
- [ ] Deployed to staging (pending)
- [ ] Deployed to production (pending)

### Environment Variables
- Ensure `GROQ_API_KEY` is set
- Ensure service account credentials in Azure Key Vault
- Ensure `YOUTUBE_CREDENTIALS` or similar env var configured

### Monitoring Points
- Monitor logs for OAuth2 validation messages
- Alert on repeated token refresh failures
- Track bot detection error rates (should decrease)
- Monitor video download success rates

---

## Related Documents

- **IMPLEMENTATION_PROGRESS_TRACKER.md** - Main task tracking document
- **PHASE_1_COMPLETION_SUMMARY.md** - Detailed Phase 1 summary
- **BOT_DETECTION_ROOT_CAUSE_ANALYSIS.md** - Original problem analysis

---

## Commit Message

```
feat: Fix YouTube bot detection in video transcript extraction

Phase 1 of lesson generation improvements. Addresses critical bot detection
issues preventing video transcription via OAuth2 authentication and yt-dlp.

Changes:
- Add OAuth2 cookies file validation (1.1)
- Add User-Agent header to yt-dlp requests (1.2)
- Improve error visibility by removing --quiet (1.3)
- Add socket timeout to prevent hangs (1.4)
- Add OAuth2 token refresh before downloads (1.5)
- Remove unnecessary -U update check (1.6)

Expected improvements:
- Bot detection success rate: 40-50% ’ >90%
- Token validity: Stale tokens ’ Always fresh
- Error visibility: Silent failures ’ Clear logs
- Network efficiency: Fewer unnecessary requests

Fixes: #bot-detection, #video-transcription, #oauth2

Related files:
- skillsync-be/helpers/youtube/groq_transcription.py
```

---

**Document Version**: 1.0
**Created**: November 12, 2025
**Status**:  READY FOR DEPLOYMENT

*Next Phase*: Phase 2 - Research Filters & Compensation
