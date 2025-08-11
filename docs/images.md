### Image Catalog

Manage versioned base images with checksum verification.

#### API Endpoints

- `GET /redfish/v1/Oem/HawkFish/Images` - List all images
- `POST /redfish/v1/Oem/HawkFish/Images` - Add a new image
- `GET /redfish/v1/Oem/HawkFish/Images/{id}` - Get image details
- `DELETE /redfish/v1/Oem/HawkFish/Images/{id}` - Remove an image
- `POST /redfish/v1/Oem/HawkFish/Images/Actions/Prune` - Remove unreferenced images

#### Image Schema

```json
{
  "Name": "ubuntu",
  "Version": "22.04",
  "URL": "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img",
  "SHA256": "a1b2c3d4...",
  "Labels": {
    "os": "ubuntu",
    "arch": "amd64"
  }
}
```

#### Features

- **Checksum Verification**: Images are verified against provided SHA256 hashes
- **Automatic Download**: Images from URLs are downloaded and cached locally
- **Garbage Collection**: Prune action removes unreferenced images (safe guard)
- **Versioning**: Multiple versions of the same image can coexist

#### CLI Usage

```bash
# List images
hawkfish images

# Add an image
hawkfish image-add ubuntu 22.04 --url https://example.com/image.img --sha256 abc123...

# Remove an image
hawkfish image-rm <image-id>
```
