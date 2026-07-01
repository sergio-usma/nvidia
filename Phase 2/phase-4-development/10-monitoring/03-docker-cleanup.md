# Docker Cleanup

Keep your Jetson clean by removing unused containers, images, and volumes.

## Check Disk Usage

```bash
docker system df
```

Shows:
- Images size
- Containers size
- Local volumes size

## Clean Up Commands

### Remove Stopped Containers

```bash
docker container prune
```

### Remove Unused Images

```bash
docker image prune -a
```

### Remove Unused Volumes

```bash
docker volume prune
```

### Full Cleanup

```bash
docker system prune -a
```

This removes:
- All stopped containers
- All unused networks
- All dangling images
- All build cache

Add `-v` to also remove volumes:

```bash
docker system prune -a -v
```

## Clean Specific Items

### Remove Specific Container

```bash
docker rm container_name
```

### Remove Specific Image

```bash
docker rmi image_name
```

### Remove Specific Volume

```bash
docker volume rm volume_name
```

## Best Practices

1. **Regular cleanup**: Run `docker system prune` monthly
2. **Check first**: Use `docker system df` before cleaning
3. **Keep running**: Don't remove images for containers you use
4. **Use volumes**: For persistent data (models, databases)

## Automatic Cleanup

Set up a cron job for weekly cleanup:

```bash
crontab -e
```

Add:

```
0 0 * * 0 docker system prune -a -f
```

This runs every Sunday at midnight.

## Next Steps

- [Firewall Setup](../part-10-security/01-firewall-setup.md)
- [Service Management](../part-10-security/02-service-management.md)
