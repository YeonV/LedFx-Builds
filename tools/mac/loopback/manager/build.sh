#!/bin/bash
swiftc ./audio_manager.swift -o audio_manager

# Sign the binary with Developer ID certificate
codesign --force --sign "Developer ID Application: Yeon Varapragasam (M349WJSL2N)" audio_manager