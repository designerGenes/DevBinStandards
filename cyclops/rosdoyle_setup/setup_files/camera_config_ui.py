#!/usr/bin/env python3
"""
Simple Web UI for Pi Camera Configuration
Allows editing camera settings and restarting the service.
"""

from flask import Flask, render_template_string, request, redirect, url_for
import os
import subprocess

app = Flask(__name__)

CONFIG_FILE = '/etc/pi_camera_capture.conf'

PRESETS = {
    'default': {
        'WIDTH': '800', 'HEIGHT': '600', 'FPS': '8', 'BITRATE': '1000000', 'ROTATION': '0',
        'HW_ENCODE': '0', 'SHUTTER': '50000', 'GAIN': '4', 'AWBMODE': 'greyworld', 'AWBGAINS': '1.5,1.0',
        'EV': '0', 'METERING': 'centre', 'SATURATION': '1.0', 'DENOISE': 'cdn_off',
        'BRIGHTNESS': '0.1', 'CONTRAST': '1.2', 'LENS_SHADING_FILE': '/home/jadennation/lens_shading_calibration/pi5_imx219_original.json'
    },
    'lowlight': {
        'WIDTH': '800', 'HEIGHT': '600', 'FPS': '8', 'BITRATE': '1000000', 'ROTATION': '0',
        'HW_ENCODE': '0', 'SHUTTER': '100000', 'GAIN': '8', 'AWBMODE': 'greyworld', 'AWBGAINS': '1.5,1.0',
        'EV': '0', 'METERING': 'centre', 'SATURATION': '1.0', 'DENOISE': 'cdn_off',
        'BRIGHTNESS': '0.2', 'CONTRAST': '1.5', 'LENS_SHADING_FILE': '/home/jadennation/lens_shading_calibration/pi5_imx219_original.json'
    },
    'daytime': {
        'WIDTH': '800', 'HEIGHT': '600', 'FPS': '8', 'BITRATE': '1000000', 'ROTATION': '0',
        'HW_ENCODE': '0', 'SHUTTER': '25000', 'GAIN': '2', 'AWBMODE': 'greyworld', 'AWBGAINS': '1.5,1.0',
        'EV': '0', 'METERING': 'centre', 'SATURATION': '1.0', 'DENOISE': 'cdn_off',
        'BRIGHTNESS': '0.0', 'CONTRAST': '1.0', 'LENS_SHADING_FILE': '/home/jadennation/lens_shading_calibration/pi5_imx219_original.json'
    }
}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Pi Camera Configuration</title>
    <script src="http://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { display: flex; gap: 20px; }
        .form-section { flex: 1; }
        .stream-section { flex: 1; }
        .form-group { margin: 10px 0; }
        label { display: inline-block; width: 120px; }
        input, select { width: 200px; }
        button { margin: 10px 5px; padding: 10px 20px; }
        .status { margin: 20px 0; padding: 10px; border: 1px solid #ccc; }
        video { width: 100%; max-width: 640px; }
    </style>
</head>
<body>
    <h1>Pi Camera Configuration</h1>
    
    <div class="container">
        <div class="form-section">
            <h2>Settings</h2>
            
            <div class="status">
                <p>Service: {{ service_status }}</p>
            </div>
            
            <form method="post">
                <div class="form-group">
                    <label for="preset">Preset:</label>
                    <select id="preset" name="preset" onchange="loadPreset()">
                        <option value="custom" {% if preset == 'custom' %}selected{% endif %}>Custom</option>
                        <option value="default" {% if preset == 'default' %}selected{% endif %}>Default</option>
                        <option value="lowlight" {% if preset == 'lowlight' %}selected{% endif %}>Low Light</option>
                        <option value="daytime" {% if preset == 'daytime' %}selected{% endif %}>Daytime</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="width">Width:</label>
                    <input type="number" id="width" name="width" value="{{ config.get('WIDTH', '800') }}">
                </div>
                
                <div class="form-group">
                    <label for="height">Height:</label>
                    <input type="number" id="height" name="height" value="{{ config.get('HEIGHT', '600') }}">
                </div>
                
                <div class="form-group">
                    <label for="fps">FPS:</label>
                    <input type="number" id="fps" name="fps" value="{{ config.get('FPS', '8') }}">
                </div>
                
                <div class="form-group">
                    <label for="bitrate">Bitrate:</label>
                    <input type="number" id="bitrate" name="bitrate" value="{{ config.get('BITRATE', '1000000') }}">
                </div>
                
                <div class="form-group">
                    <label for="rotation">Rotation:</label>
                    <select id="rotation" name="rotation">
                        <option value="0" {% if config.get('ROTATION', '1') == '0' %}selected{% endif %}>0°</option>
                        <option value="1" {% if config.get('ROTATION', '1') == '1' %}selected{% endif %}>90°</option>
                        <option value="2" {% if config.get('ROTATION', '1') == '2' %}selected{% endif %}>180°</option>
                        <option value="3" {% if config.get('ROTATION', '1') == '3' %}selected{% endif %}>270°</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="shutter">Shutter (μs):</label>
                    <input type="number" id="shutter" name="shutter" value="{{ config.get('SHUTTER', '50000') }}">
                </div>
                
                <div class="form-group">
                    <label for="gain">Gain:</label>
                    <input type="number" step="0.1" id="gain" name="gain" value="{{ config.get('GAIN', '4') }}">
                </div>
                
                <div class="form-group">
            <label for="awbmode">AWB Mode:</label>
            <select id="awbmode" name="awbmode">
                <option value="fixed" {% if config.get('AWBMODE', 'fixed') == 'fixed' %}selected{% endif %}>Fixed</option>
                <option value="auto" {% if config.get('AWBMODE', 'fixed') == 'auto' %}selected{% endif %}>Auto</option>
            </select>
        </div>
        
        <div class="form-group">
            <label for="awbgains">AWB Gains (if fixed):</label>
            <input type="text" id="awbgains" name="awbgains" value="{{ config.get('AWBGAINS', '1.2,1.5') }}">
        </div>
        
        <div class="form-group">
            <label for="ev">Exposure Compensation (EV):</label>
            <input type="number" step="0.1" id="ev" name="ev" value="{{ config.get('EV', '0') }}">
        </div>
        
        <div class="form-group">
            <label for="metering">Metering:</label>
            <select id="metering" name="metering">
                <option value="centre" {% if config.get('METERING', 'centre') == 'centre' %}selected{% endif %}>Centre</option>
                <option value="spot" {% if config.get('METERING', 'centre') == 'spot' %}selected{% endif %}>Spot</option>
                <option value="average" {% if config.get('METERING', 'centre') == 'average' %}selected{% endif %}>Average</option>
                <option value="custom" {% if config.get('METERING', 'centre') == 'custom' %}selected{% endif %}>Custom</option>
            </select>
        </div>
        
        <div class="form-group">
            <label for="saturation">Saturation:</label>
            <input type="number" step="0.1" id="saturation" name="saturation" value="{{ config.get('SATURATION', '1.0') }}">
                
                <div class="form-group">
                    <label for="denoise">Denoise:</label>
                    <input type="text" id="denoise" name="denoise" value="{{ config.get('DENOISE', 'cdn_off') }}">
                </div>
                
                <div class="form-group">
                    <label for="brightness">Brightness:</label>
                    <input type="number" step="0.1" id="brightness" name="brightness" value="{{ config.get('BRIGHTNESS', '0.1') }}">
                </div>
                
                <div class="form-group">
                    <label for="contrast">Contrast:</label>
                    <input type="number" step="0.1" id="contrast" name="contrast" value="{{ config.get('CONTRAST', '1.2') }}">
                </div>
                
                <div class="form-group">
                    <label for="lens_shading_file">Lens Shading File:</label>
                    <input type="text" id="lens_shading_file" name="lens_shading_file" value="{{ config.get('LENS_SHADING_FILE', '/home/jadennation/lens_shading_calibration/pi5_imx219_original.json') }}" size="60">
                </div>
                
                <button type="submit" name="action" value="save">Save Configuration</button>
                <button type="submit" name="action" value="restart">Save and Restart Service</button>
            </form>
            
            {% if message %}
            <div class="status">
                <p>{{ message }}</p>
            </div>
            {% endif %}
        </div>
        
        <div class="stream-section">
            <h2>Live Stream</h2>
            <video id="video" controls autoplay muted></video>
            <br>
            <button onclick="loadStream()">Reload Stream</button>
        </div>
    </div>
    
    <script>
        const presets = {
            default: {
                width: '800', height: '600', fps: '8', bitrate: '1000000', rotation: '0',
                shutter: '50000', gain: '4', awbmode: 'auto', awbgains: '1.2,1.5', ev: '0',
                metering: 'centre', saturation: '1.0', denoise: 'cdn_off', brightness: '0.1', contrast: '1.2'
            },
            lowlight: {
                width: '800', height: '600', fps: '8', bitrate: '1000000', rotation: '0',
                shutter: '100000', gain: '8', awbmode: 'auto', awbgains: '1.2,1.5', ev: '0',
                metering: 'centre', saturation: '1.0', denoise: 'cdn_off', brightness: '0.2', contrast: '1.5'
            },
            daytime: {
                width: '800', height: '600', fps: '8', bitrate: '1000000', rotation: '0',
                shutter: '25000', gain: '2', awbmode: 'auto', awbgains: '1.2,1.5', ev: '0',
                metering: 'centre', saturation: '1.0', denoise: 'cdn_off', brightness: '0.0', contrast: '1.0'
            }
        };
        
        function loadPreset() {
            const preset = document.getElementById('preset').value;
            if (preset !== 'custom' && presets[preset]) {
                const config = presets[preset];
                Object.keys(config).forEach(key => {
                    const element = document.getElementById(key);
                    if (element) {
                        element.value = config[key];
                    }
                });
            }
        }
        
        const video = document.getElementById('video');
        // Use relative protocol to support both http and https (if proxied)
        // Construct stream URL based on current page hostname
        const videoSrc = '//' + window.location.hostname + ':8889/camera/index.m3u8';
        console.log('Video src:', videoSrc);
        
        let hls = null;
        
        function loadStream() {
            console.log('Loading stream...');
            if (hls) {
                hls.destroy();
            }
            
            if (Hls.isSupported()) {
                console.log('HLS supported');
                hls = new Hls({
                    debug: false,
                    manifestLoadingTimeOut: 10000,
                    manifestLoadingMaxRetry: 10,
                    levelLoadingTimeOut: 10000,
                    levelLoadingMaxRetry: 10
                });
                hls.loadSource(videoSrc);
                hls.attachMedia(video);
                hls.on(Hls.Events.MANIFEST_PARSED, function() {
                    console.log('Manifest parsed, playing video');
                    video.play().catch(e => console.error("Play failed:", e));
                });
                hls.on(Hls.Events.ERROR, function(event, data) {
                    if (data.fatal) {
                        switch (data.type) {
                        case Hls.ErrorTypes.NETWORK_ERROR:
                            console.log("fatal network error encountered, trying to recover");
                            hls.startLoad();
                            break;
                        case Hls.ErrorTypes.MEDIA_ERROR:
                            console.log("fatal media error encountered, trying to recover");
                            hls.recoverMediaError();
                            break;
                        default:
                            console.log("cannot recover");
                            hls.destroy();
                            break;
                        }
                    }
                });
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                console.log('Native HLS support');
                video.src = videoSrc;
                video.addEventListener('loadedmetadata', function() {
                    console.log('Metadata loaded, playing video');
                    video.play();
                });
                video.addEventListener('error', function(e) {
                    console.error('Video error:', e);
                });
            } else {
                console.log('HLS not supported');
                document.querySelector('.stream-section').innerHTML += '<p style="color:red">HLS not supported in this browser.</p>';
            }
        }
        
        loadStream();
        
        // Retry loading stream after 5 seconds in case it wasn't ready
        setTimeout(() => {
            console.log('Retrying stream load...');
            if (video.paused) {
                 loadStream();
            }
        }, 5000);
        
        // Reload stream after form submission
        window.addEventListener('load', function() {
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('reloaded')) {
                loadStream();
            }
        });
    </script>
</body>
</html>
'''

def load_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config

def save_config(config):
    config_content = '\n'.join(f'{key}={value}' for key, value in config.items()) + '\n'
    result = subprocess.run(['sudo', 'sh', '-c', f'cat > {CONFIG_FILE}'], 
                          input=config_content, text=True, capture_output=True)
    if result.returncode != 0:
        raise Exception(f'Failed to save config: {result.stderr}')

def get_service_status():
    try:
        result = subprocess.run(['systemctl', 'is-active', 'pi_camera_capture'], 
                              capture_output=True, text=True)
        return 'Active' if result.returncode == 0 else 'Inactive'
    except:
        return 'Unknown'

@app.route('/camera/')
def camera():
    config = load_config()
    service_status = get_service_status()
    return render_template_string(HTML_TEMPLATE, config=config, service_status=service_status, message=None)

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        preset = request.form.get('preset', 'custom')
        
        if preset in PRESETS:
            config = PRESETS[preset].copy()
            message = f'Loaded {preset} preset.'
        else:
            config = {
                'WIDTH': request.form['width'],
                'HEIGHT': request.form['height'],
                'FPS': request.form['fps'],
                'BITRATE': request.form['bitrate'],
                'ROTATION': request.form['rotation'],
                'HW_ENCODE': '0',
                'SHUTTER': request.form['shutter'],
                'GAIN': request.form['gain'],
                'AWBMODE': request.form['awbmode'],
                'AWBGAINS': request.form['awbgains'],
                'EV': request.form['ev'],
                'METERING': request.form['metering'],
                'SATURATION': request.form['saturation'],
                'DENOISE': request.form['denoise'],
                'BRIGHTNESS': request.form['brightness'],
                'CONTRAST': request.form['contrast'],
                'LENS_SHADING_FILE': request.form['lens_shading_file']
            }
        
        try:
            save_config(config)
            message = message or 'Configuration saved successfully.'
            
            if action == 'restart':
                subprocess.run(['sudo', 'systemctl', 'restart', 'pi_camera_capture'])
                message += ' Service restarted.'
        except Exception as e:
            message = f'Error: {str(e)}'
    
    config = load_config()
    service_status = get_service_status()
    
    # Determine current preset
    preset = 'custom'
    for p_name, p_config in PRESETS.items():
        if all(config.get(k) == v for k, v in p_config.items()):
            preset = p_name
            break
    
    return render_template_string(HTML_TEMPLATE, config=config, service_status=service_status, message=message, preset=preset)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888, debug=False)