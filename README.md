# Buzzer Game Application

A real-time buzzer application for quiz competitions and games.

## AWS t2.micro Deployment Specifications

This application is optimized to run on AWS t2.micro instances with the following specifications:
- Maximum concurrent rooms: 50
- Maximum players per room: 30
- Inactive room cleanup: 1 hour
- Maximum concurrent connections: ~1500 (across all rooms)

### Resource Usage
- Memory: Optimized to stay under 1GB RAM
- CPU: Uses 2 worker processes to maximize t2.micro's 1 vCPU
- Network: WebSocket connections optimized for low memory footprint

## Deployment Instructions

1. Launch an AWS t2.micro instance with Ubuntu
2. Clone this repository:
   ```bash
   git clone <your-repo-url>
   cd buzzzer
   ```

3. Run the deployment script:
   ```bash
   ./deploy.sh
   ```

The script will:
- Install all necessary dependencies
- Configure Nginx as a reverse proxy
- Set up the application as a systemd service
- Start the application on port 80

### Monitoring

Check application status:
```bash
sudo systemctl status buzzer
```

View logs:
```bash
sudo journalctl -u buzzer -f
```

### Performance Tips

- Regularly monitor memory usage with `free -m`
- Check CPU usage with `top` or `htop`
- Monitor network connections: `netstat -an | grep :80 | wc -l`
- If memory usage approaches 80%, consider cleaning up inactive rooms

### Troubleshooting

1. If the application doesn't start:
   ```bash
   sudo systemctl status buzzer
   sudo journalctl -u buzzer -e
   ```

2. If WebSocket connections fail:
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

3. Memory issues:
   - Check memory usage: `free -m`
   - List top processes: `ps aux --sort=-%mem | head`