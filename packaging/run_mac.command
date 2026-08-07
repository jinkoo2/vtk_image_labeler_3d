#!/bin/bash
# Clear Gatekeeper quarantine and launch Image Labeler 3D.
cd "$(dirname "$0")"
xattr -cr . 2>/dev/null || true
chmod +x ./ImageLabeler3D 2>/dev/null || true
exec ./ImageLabeler3D "$@"
