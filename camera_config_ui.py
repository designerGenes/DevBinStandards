#!/usr/bin/env python3
from flask import Flask, request, render_template_string
import subprocess
import os

app = Flask(__name__)
CONFIG_FILE = "/etc/pi_camera_capture.conf"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pi Camera Configuration</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .dark-mode { background-color: #222; color: #eee; }
        .container { display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-start; }
        .form-section { flex: 1 1 360px; min-width: 280px; }
        .stream-section { flex: 1 1 360px; min-width: 280px; }
        .form-group { margin: 10px 0; display:flex; align-items:center; }
        label { display: inline-block; width: 120px; font-weight:600; }
        input { flex: 1; padding:8px; font-size:16px; }
        button { margin: 10px 5px; padding: 10px 20px; border-radius:6px; cursor:pointer; }
        #darkModeToggle { padding:12px 18px; border-radius:8px; background:#eee; border:1px solid #999; }
        h1 { font-size: 36px; margin-top: 10px; }
        h2 { font-size: 28px; }
        video { width: 100%; max-width: 800px; background:#000; height:auto; display:block; }
        #streamStatus { margin-top:10px; color:#a00; font-weight:600; }
    </style>
</head>
<body>
    <button id="darkModeToggle">Dark Mode</button>
    <h1>Pi Camera Configuration</h1>
    {% if status %}
    <div id="status" style="margin:10px 0;padding:10px;border-radius:6px;background:#fee;color:#600;font-weight:700;">{{ status }}</div>
    {% endif %}
    
    <div class="container">
        <div class="form-section">
            <form method="post">
                <div class="form-group"><label>Width:</label><input name="width" value="{{ config.get('WIDTH', '800') }}"></div>
                <div class="form-group"><label>Height:</label><input name="height" value="{{ config.get('HEIGHT', '600') }}"></div>
                <div class="form-group"><label>FPS:</label><input name="fps" value="{{ config.get('FPS', '8') }}"></div>
                <div class="form-group"><label>Bitrate:</label><input name="bitrate" value="{{ config.get('BITRATE', '1000000') }}"></div>
                <div class="form-group"><label>Shutter:</label><input name="shutter" value="{{ config.get('SHUTTER', '100000') }}"></div>
                <div class="form-group"><label>Gain:</label><input name="gain" value="{{ config.get('GAIN', '8') }}"></div>
                <div class="form-group"><label>AWB Gains:</label><input name="awbgains" value="{{ config.get('AWBGAINS', '1.5,1.0') }}"></div>
                <div class="form-group"><label>Lens Shading:</label><input name="lens_shading_file" value="{{ config.get('LENS_SHADING_FILE', '') }}" size="50"></div>
                <button type="submit" name="action" value="save">Save</button>
                <button type="submit" name="action" value="restart">Save & Restart</button>
            </form>
        </div>
        
        <div class="stream-section">
            <h2>Live Stream</h2>
            <video id="video" controls autoplay muted playsinline></video>
            <div id="streamStatus">&nbsp;</div>
            <button onclick="loadStream()">Reload Stream</button>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <script>
        function getStreamURL() {
            const host = window.location.hostname;
            const port = window.location.port ? window.location.port : '8889';
            return `http://${host}:${port}/camera/index.m3u8`;
        }

        // Check playlist availability before trying to attach player
        async function checkPlaylist(url) {
            try {
                const res = await fetch(url, { method: 'GET', cache: 'no-store' });
                return res.ok;
            } catch (e) {
                return false;
            }
        }

        let hlsInstance = null;
        async function loadStream() {
            const video = document.getElementById('video');
            const status = document.getElementById('streamStatus');
            const streamUrl = getStreamURL();

            status.textContent = 'Checking stream...';
            const available = await checkPlaylist(streamUrl);
            if (!available) {
                status.textContent = 'No stream available right now. Retrying in 5s...';
                // clear any existing src/hls
                if (hlsInstance) { try { hlsInstance.destroy(); } catch(e){} hlsInstance = null; }
                video.removeAttribute('src');
                setTimeout(loadStream, 5000);
                return;
            }

            status.textContent = 'Stream found — starting playback';

            if (video.canPlayType('application/vnd.apple.mpegurl')) {
                video.src = streamUrl;
                video.play().catch(()=>{});
                status.textContent = '';
            } else if (window.Hls) {
                try {
                    if (hlsInstance) {
                        hlsInstance.destroy();
                        hlsInstance = null;
                    }
                    hlsInstance = new Hls({ maxBufferLength: 30 });
                    hlsInstance.on(Hls.Events.ERROR, function (event, data) {
                        console.error('Hls error', event, data);
                        status.textContent = 'Playback error. Retrying in 5s...';
                        setTimeout(loadStream, 5000);
                    });
                    hlsInstance.loadSource(streamUrl);
                    hlsInstance.attachMedia(video);
                    hlsInstance.on(Hls.Events.MANIFEST_PARSED, function() { video.play().catch(()=>{}); status.textContent = ''; });
                } catch (e) {
                    status.textContent = 'Failed to play stream: ' + e.message;
                }
            } else {
                status.textContent = 'HLS not supported in this browser. Try Safari or install Hls.js.';
            }
        }

        function toggleDarkMode() {
            const isDark = document.body.classList.toggle('dark-mode');
            localStorage.setItem('darkMode', isDark);
            document.getElementById('darkModeToggle').textContent = isDark ? 'Light Mode' : 'Dark Mode';
        }

        if (localStorage.getItem('darkMode') === 'true') {
            document.body.classList.add('dark-mode');
            document.getElementById('darkModeToggle').textContent = 'Light Mode';
        }

        document.getElementById('darkModeToggle').addEventListener('click', toggleDarkMode);
        loadStream();
    </script>
</body>
</html>
"""

def load_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    return config

def save_config(config):
    # Write to a temp file then move into place using sudo to avoid permission errors
    import tempfile
    tmp_path = None
    fd = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix='pi_camera_capture.', suffix='.conf', text=True)
        with os.fdopen(fd, 'w') as f:
            for key, value in config.items():
                f.write(f'{key}={value}\n')
            f.flush()
            os.fsync(f.fileno())
        # Move into place with sudo and set ownership/permissions
        res = subprocess.run(['sudo', 'mv', tmp_path, CONFIG_FILE], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"sudo mv failed: {res.stderr.strip()}")
        subprocess.run(['sudo', 'chown', 'root:root', CONFIG_FILE])
        subprocess.run(['sudo', 'chmod', '644', CONFIG_FILE])
        return True
    finally:
        # Clean up temp file if it still exists
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

@app.route('/', methods=['GET', 'POST'])
def index():
    config = load_config()
    status = None
    
    if request.method == 'POST':
        for key in request.form:
            if key != 'action':
                config[key.upper()] = request.form[key]
        try:
            saved = save_config(config)
            if saved:
                status = 'Configuration saved.'
            else:
                status = 'Configuration not saved.'
        except Exception as e:
            app.logger.error('Failed to save configuration: %s', e)
            status = f'Failed to save configuration: {e}'
            # Continue and render page with an error message (don't return HTTP 500)
            # fall through to render_template_string at the end of the view
        
        if request.form.get('action') == 'restart':
            try:
                subprocess.run(['sudo', 'systemctl', 'restart', 'pi_camera_capture.service'], check=True)
                status += ' Service restarted.'
            except Exception as e:
                app.logger.error('Failed to restart service: %s', e)
                status += f' (failed to restart: {e})'
    
    return render_template_string(HTML_TEMPLATE, config=config, status=status)

REBOOT_TOKEN_FILE = "/etc/pi_reboot_token"

import secrets, hmac

@app.route('/admin/reboot', methods=['POST'])
def admin_reboot():
    """Protected reboot endpoint.

    Call with header: Authorization: Bearer <token>
    The token is stored on the device at /etc/pi_reboot_token (root:root, 600).
    """
    # Get token from Authorization header or form
    auth = request.headers.get('Authorization', '')
    token = None
    if auth.startswith('Bearer '):
        token = auth.split(' ', 1)[1].strip()
    else:
        token = request.form.get('token') or request.args.get('token')

    # Load expected token
    try:
        with open(REBOOT_TOKEN_FILE, 'r') as f:
            expected = f.read().strip()
    except Exception as e:
        app.logger.error('Reboot token missing or unreadable: %s', e)
        return ('Reboot token not configured on device', 503)

    if not token or not hmac.compare_digest(token, expected):
        app.logger.warning('Unauthorized reboot attempt from %s', request.remote_addr)
        return ('Forbidden', 403)

    # Authorized — trigger reboot (asynchronously)
    try:
        # Use sudo to perform the reboot, service should have sudoers configured
        subprocess.Popen(['sudo', '/sbin/shutdown', '-r', 'now'])
        app.logger.info('Reboot triggered by %s', request.remote_addr)
        return ('Rebooting', 202)
    except Exception as e:
        app.logger.error('Failed to trigger reboot: %s', e)
        return (f'Failed to trigger reboot: {e}', 500)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)