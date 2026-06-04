# Deployment Guide

## Local Development

```bash
docker-compose up -d
```

## Cloud Deployment

### Railway
```bash
railway init
railway up
```

### Render
1. Connect GitHub repo
2. Deploy from docker-compose.yml

### AWS EC2
```bash
# t3.medium ($30/month)
sudo apt update
sudo apt install docker.io docker-compose
docker-compose up -d
```

## Production Checklist
- [ ] Enable HTTPS
- [ ] Set up backups
- [ ] Configure monitoring
- [ ] Use environment variables
- [ ] Enable authentication
