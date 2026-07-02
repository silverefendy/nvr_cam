import 'package:flutter/material.dart';
import 'package:flutter_vlc_player/flutter_vlc_player.dart';
import '../models/camera.dart';
import '../services/api_service.dart';

class CameraViewScreen extends StatefulWidget {
  final Camera camera;

  const CameraViewScreen({super.key, required this.camera});

  @override
  State<CameraViewScreen> createState() => _CameraViewScreenState();
}

class _CameraViewScreenState extends State<CameraViewScreen> {
  late VlcPlayerController _vlcPlayerController;
  final ApiService _apiService = ApiService();
  bool _isLoading = true;
  bool _hasError = false;

  @override
  void initState() {
    super.initState();
    _initializePlayer();
  }

  Future<void> _initializePlayer() async {
    await _apiService.init();
    final streamUrl = _apiService.getStreamUrl(widget.camera.id);

    _vlcPlayerController = VlcPlayerController.network(
      streamUrl,
      autoPlay: true,
      options: const VlcPlayerOptions(
        advanced: VlcAdvancedOptions([
          '--rtsp-tcp',
          '--network-caching=300',
        ]),
      ),
    );

    try {
      await _vlcPlayerController.initialize();
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _hasError = true;
        });
      }
    }
  }

  @override
  void dispose() {
    _vlcPlayerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.camera.name),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              setState(() {
                _isLoading = true;
                _hasError = false;
              });
              _initializePlayer();
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _hasError
              ? _buildErrorView()
              : _buildVideoView(),
    );
  }

  Widget _buildErrorView() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.error_outline,
            size: 64,
            color: Colors.red,
          ),
          const SizedBox(height: 16),
          const Text('Failed to load stream'),
          const SizedBox(height: 8),
          Text(
            widget.camera.isOnline ? 'Camera is online but stream unavailable' : 'Camera is offline',
            style: const TextStyle(color: Colors.grey),
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: () {
              setState(() {
                _isLoading = true;
                _hasError = false;
              });
              _initializePlayer();
            },
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildVideoView() {
    return Center(
      child: AspectRatio(
        aspectRatio: 16 / 9,
        child: VlcPlayer(
          controller: _vlcPlayerController,
          aspectRatio: 16 / 9,
          virtualDisplay: true,
        ),
      ),
    );
  }
}
