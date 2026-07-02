import 'package:flutter/material.dart';
import 'package:flutter_vlc_player/flutter_vlc_player.dart';
import 'package:intl/intl.dart';
import '../models/camera.dart';
import '../services/api_service.dart';

class PlaybackScreen extends StatefulWidget {
  const PlaybackScreen({super.key});
  @override
  State<PlaybackScreen> createState() => _PlaybackScreenState();
}

class _PlaybackScreenState extends State<PlaybackScreen> {
  final ApiService _apiService = ApiService();
  List<Camera> _cameras = [];
  Camera? _selectedCamera;
  DateTime _selectedDate = DateTime.now();
  List<Map<String, dynamic>> _recordings = [];
  VlcPlayerController? _vlcController;
  bool _isLoadingCameras = true;
  bool _isLoadingRecordings = false;
  Map<String, dynamic>? _playingRecording;

  @override
  void initState() {
    super.initState();
    _loadCameras();
  }

  Future<void> _loadCameras() async {
    await _apiService.init();
    final cameras = await _apiService.getCameras();
    if (mounted) {
      setState(() {
        _cameras = cameras;
        if (cameras.isNotEmpty) _selectedCamera = cameras.first;
        _isLoadingCameras = false;
      });
      if (_selectedCamera != null) _loadRecordings();
    }
  }

  Future<void> _loadRecordings() async {
    if (_selectedCamera == null) return;
    setState(() { _isLoadingRecordings = true; });
    final dateFrom = DateTime(_selectedDate.year, _selectedDate.month, _selectedDate.day);
    final dateTo = dateFrom.add(const Duration(days: 1));
    try {
      final recordings = await _apiService.getRecordings(
        cameraId: _selectedCamera!.id,
        dateFrom: dateFrom,
        dateTo: dateTo,
      );
      if (mounted) setState(() { _recordings = recordings; _isLoadingRecordings = false; });
    } catch (e) {
      if (mounted) setState(() { _isLoadingRecordings = false; });
    }
  }

  Future<void> _playRecording(Map<String, dynamic> recording) async {
    _vlcController?.dispose();
    final url = _apiService.getRecordingUrl(recording['id']);
    final controller = VlcPlayerController.network(
      url,
      autoPlay: true,
      options: const VlcPlayerOptions(),
    );
    await controller.initialize();
    if (mounted) setState(() { _vlcController = controller; _playingRecording = recording; });
  }

  Future<void> _pickDate() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now(),
    );
    if (date != null) {
      setState(() { _selectedDate = date; });
      _loadRecordings();
    }
  }

  @override
  void dispose() {
    _vlcController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Playback')),
      body: _isLoadingCameras
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // Controls
                Padding(
                  padding: const EdgeInsets.all(8.0),
                  child: Row(
                    children: [
                      Expanded(
                        child: DropdownButton<Camera>(
                          value: _selectedCamera,
                          isExpanded: true,
                          items: _cameras.map((c) => DropdownMenuItem(value: c, child: Text(c.name))).toList(),
                          onChanged: (c) { setState(() { _selectedCamera = c; }); _loadRecordings(); },
                        ),
                      ),
                      const SizedBox(width: 8),
                      TextButton.icon(
                        icon: const Icon(Icons.calendar_today),
                        label: Text(DateFormat('dd/MM/yyyy').format(_selectedDate)),
                        onPressed: _pickDate,
                      ),
                    ],
                  ),
                ),
                // Video player
                if (_vlcController != null)
                  AspectRatio(
                    aspectRatio: 16 / 9,
                    child: VlcPlayer(controller: _vlcController!, aspectRatio: 16/9, virtualDisplay: true),
                  ),
                // Recording list
                Expanded(
                  child: _isLoadingRecordings
                      ? const Center(child: CircularProgressIndicator())
                      : _recordings.isEmpty
                          ? const Center(child: Text('No recordings for this date'))
                          : ListView.builder(
                              itemCount: _recordings.length,
                              itemBuilder: (context, index) {
                                final rec = _recordings[index];
                                final start = DateTime.tryParse(rec['start_time'] ?? '');
                                final isPlaying = _playingRecording?['id'] == rec['id'];
                                return ListTile(
                                  leading: Icon(Icons.play_circle,
                                      color: isPlaying ? Colors.blue : Colors.grey),
                                  title: Text(start != null
                                      ? DateFormat('HH:mm:ss').format(start.toLocal())
                                      : rec['id']),
                                  subtitle: Text('${rec['duration_seconds'] ?? 0}s · ${((rec['file_size'] ?? 0) / 1024 / 1024).toStringAsFixed(1)} MB'),
                                  selected: isPlaying,
                                  onTap: () => _playRecording(rec),
                                );
                              },
                            ),
                ),
              ],
            ),
    );
  }
}
