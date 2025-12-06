# Encrypted Logging in P3-Edge

P3-Edge implements encrypted logging to protect sensitive user data in log files, including search queries, user preferences, chat messages, and system actions.

## Overview

All log files are encrypted at rest using Fernet symmetric encryption (AES-128 in CBC mode). This ensures that sensitive information like dietary preferences, shopping habits, and personal data remain protected even if log files are accessed by unauthorized parties.

## Features

- **Automatic Encryption**: Logs are encrypted before being written to disk
- **Transparent Operation**: Application code doesn't change; encryption happens at the logging layer
- **Log Rotation Support**: Encrypted logs support rotation just like plain text logs
- **Backward Compatible**: Can be disabled via configuration if needed
- **Secure Key Management**: Uses the same encryption key as database credentials

## Configuration

Encryption is controlled in `config/app_config.json`:

```json
{
  "logging": {
    "level": "INFO",
    "max_file_size_mb": 10,
    "backup_count": 5,
    "encrypt_logs": true
  }
}
```

**Options:**
- `encrypt_logs`: Set to `true` to enable encryption, `false` to disable (default: `true`)

## Log File Locations

**Encrypted Logs:**
- Main log: `logs/p3edge.log.enc`
- Rotated logs: `logs/p3edge.log.enc.1`, `logs/p3edge.log.enc.2`, etc.

**Encryption Key:**
- Location: `config/.key`
- Format: Fernet key (44 bytes, base64url encoded)
- Permissions: 600 (owner read/write only)

## Viewing Encrypted Logs

### Using the View Logs Script

The `scripts/view_logs.py` utility decrypts and displays log files:

```bash
# View all logs
python scripts/view_logs.py

# View last 50 lines
python scripts/view_logs.py --tail 50

# Filter for errors
python scripts/view_logs.py --grep "ERROR"

# Search for specific component
python scripts/view_logs.py --grep "autonomous_agent"

# View rotated log file
python scripts/view_logs.py --file logs/p3edge.log.enc.1

# Combine filters
python scripts/view_logs.py --tail 100 --grep "ERROR"
```

### Command Line Options

```
--file FILE       Path to encrypted log file (default: logs/p3edge.log.enc)
--key PATH        Path to encryption key (default: config/.key)
--tail N          Show only last N lines
--grep PATTERN    Filter lines containing PATTERN
--help            Show help message
```

### Examples

**View recent errors:**
```bash
python scripts/view_logs.py --tail 100 --grep "ERROR"
```

**Check autonomous agent activity:**
```bash
python scripts/view_logs.py --grep "autonomous_agent" --tail 50
```

**View specific rotated log:**
```bash
python scripts/view_logs.py --file logs/p3edge.log.enc.2
```

## Security Considerations

### What is Protected

Encrypted logs may contain:
- User chat messages and LLM responses
- Search queries (product searches, vendor queries)
- User preferences and dietary information
- System actions and decisions
- Tool execution details
- Error messages with sensitive context

### Key Management

The encryption key is stored at `config/.key` with restrictive permissions:
- Only the file owner can read/write
- Same key used for credential encryption
- Generated during initial database setup

### Best Practices

1. **Protect the Key File**: Ensure `config/.key` has 600 permissions
2. **Backup Encryption Key**: Store a secure backup of the key file separately
3. **Rotate Keys Periodically**: Consider key rotation for long-term deployments
4. **Secure Log Access**: Only use the view_logs.py script on trusted machines
5. **Monitor Console Output**: Console logs are NOT encrypted; sensitive data may appear there

## Disabling Encryption

To disable log encryption:

1. Edit `config/app_config.json`:
   ```json
   "logging": {
     "encrypt_logs": false
   }
   ```

2. Restart the application

3. Logs will be written to `logs/p3edge.log` in plain text

**Note:** Existing encrypted logs remain encrypted. Use `view_logs.py` to read them.

## Troubleshooting

### "Encryption key not found" Warning

**Cause:** The `config/.key` file doesn't exist.

**Solution:**
- Run the database initialization: `python scripts/init_db.py`
- This generates the encryption key

### "Failed to decrypt line" Error

**Possible causes:**
- Corrupted log file
- Wrong encryption key
- Mix of encrypted/unencrypted log entries

**Solution:**
- Verify you're using the correct key file
- Check log file integrity
- If logs are corrupted, delete and start fresh

### Logs Not Being Encrypted

**Check:**
1. Configuration: `encrypt_logs` should be `true`
2. Key file exists: `config/.key` should exist
3. Application logs: Check console for warnings
4. File extension: Encrypted logs use `.log.enc` extension

## Technical Details

### Encryption Algorithm

- **Algorithm**: Fernet (symmetric encryption)
- **Cipher**: AES-128-CBC with HMAC-SHA256 authentication
- **Key Size**: 128 bits (Fernet standard)
- **Encoding**: Base64url for key, Base64 for encrypted data

### Log Format

Each log line is:
1. Formatted as plain text by the logging formatter
2. Encrypted using Fernet
3. Encoded as base64
4. Written as a single line with newline delimiter

**Structure:**
```
[base64(fernet_encrypt(log_message))]\n
```

This allows:
- Line-by-line decryption
- Log rotation to work normally
- Efficient random access to log entries

### Performance Impact

Encryption adds minimal overhead:
- ~0.1ms per log entry on modern hardware
- Negligible impact on application performance
- Slightly larger file size due to base64 encoding (~33% increase)

## Privacy Implications

### What Gets Logged

The application logs various activities that may contain sensitive data:

**DEBUG Level** (file only):
- LLM message content (truncated to 200 chars)
- Search queries
- Tool execution details

**INFO Level:**
- System events
- User actions
- Successful operations

**ERROR Level:**
- Exception messages
- Stack traces
- Failed operations

### Retention Policy

- **Conversation Data**: Auto-purged after 30 days (configurable)
- **Log Files**: Rotated based on size (10 MB default)
- **Backup Count**: 5 rotated logs retained (configurable)

Total log storage: ~60 MB maximum (6 files × 10 MB)

## Integration with Database Encryption

P3-Edge uses a layered encryption approach:

1. **Database Encryption**: SQLCipher with AES-256
   - All user data encrypted at rest
   - Separate encryption from logs

2. **Log Encryption**: Fernet with AES-128
   - Protects sensitive data in logs
   - Same key as credential file

3. **Credential Encryption**: Fernet for API keys
   - Stored in `config/credentials.enc`
   - Same key as logs

This ensures comprehensive data protection across all storage.
