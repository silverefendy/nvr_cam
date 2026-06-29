# NVR Cam Mobile App

Flutter mobile application for viewing CCTV feeds and managing cameras remotely.

## Features

- **Live View**: Watch real-time camera feeds using VLC player
- **Camera Grid**: View all cameras in a grid layout with status indicators
- **Authentication**: Secure login with JWT tokens
- **Responsive UI**: Material Design 3 with dark mode support
- **Offline Detection**: Shows camera online/offline status

## Prerequisites

- Flutter SDK 3.0.0 or higher
- Android Studio / Xcode for mobile development
- A running NVR Cam backend server

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nvr_cam.git
cd nvr_cam/mobile
```

2. Install dependencies:
```bash
flutter pub get
```

3. Run the app:
```bash
# For Android
flutter run

# For iOS
flutter run -d ios
```

## Configuration

On first launch, you'll need to provide:
- **Server URL**: The URL of your NVR Cam backend (e.g., https://nvr.example.com)
- **Username**: Your NVR Cam username
- **Password**: Your NVR Cam password

The app will store these credentials securely using SharedPreferences.

## Building for Release

### Android
```bash
flutter build apk --release
```

### iOS
```bash
flutter build ios --release
```

## Architecture

- **State Management**: Riverpod
- **HTTP Client**: Dio
- **Video Player**: flutter_vlc_player (for RTSP streaming)
- **Storage**: shared_preferences

## Project Structure

```
lib/
├── main.dart              # App entry point
├── models/
│   └── camera.dart        # Camera data model
├── services/
│   └── api_service.dart   # API communication
└── screens/
    ├── splash_screen.dart
    ├── login_screen.dart
    ├── home_screen.dart
    └── camera_view_screen.dart
```

## API Endpoints Used

- `POST /api/v1/auth/login` - User authentication
- `GET /api/v1/config/cameras` - Get camera list
- `GET /api/v1/stream/live/{id}` - Get live stream URL
- `GET /api/v1/system/health` - System health check

## Troubleshooting

### Stream not loading
- Ensure the backend server is accessible
- Check that the camera is online
- Verify RTSP stream is working on the backend

### Login failed
- Verify server URL is correct (include https://)
- Check username and password
- Ensure backend is running

## License

This project is part of the NVR Cam system.
