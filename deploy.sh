#!/bin/bash

# Update system and install dependencies
sudo apt-get update
sudo apt-get install -y python3-pip nginx

# Install Python dependencies
pip3 install -r requirements.txt

# Configure Nginx as reverse proxy
sudo tee /etc/nginx/sites-available/buzzer << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

# Enable the Nginx site
sudo ln -sf /etc/nginx/sites-available/buzzer /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

# Create systemd service for the application
sudo tee /etc/systemd/system/buzzer.service << EOF
[Unit]
Description=Buzzer Game Application
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(python3 -m site --user-base)/bin:$PATH"
ExecStart=$(which gunicorn) --worker-class eventlet -w 2 --bind 127.0.0.1:5001 app:app --config gunicorn.conf.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start and enable the service
sudo systemctl daemon-reload
sudo systemctl start buzzer
sudo systemctl enable buzzer

echo "Deployment complete! The application should be running on port 80"