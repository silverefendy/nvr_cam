import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';

class EventsScreen extends StatefulWidget {
  const EventsScreen({super.key});
  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  final ApiService _apiService = ApiService();
  List<Map<String, dynamic>> _events = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadEvents();
  }

  Future<void> _loadEvents() async {
    await _apiService.init();
    try {
      final events = await _apiService.getEvents();
      if (mounted) setState(() { _events = events; _isLoading = false; });
    } catch (e) {
      if (mounted) setState(() { _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Motion Events'),
        actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _loadEvents)],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _events.isEmpty
              ? const Center(child: Text('No events found'))
              : RefreshIndicator(
                  onRefresh: _loadEvents,
                  child: ListView.builder(
                    itemCount: _events.length,
                    itemBuilder: (context, index) {
                      final event = _events[index];
                      final ts = DateTime.tryParse(event['timestamp'] ?? '');
                      return ListTile(
                        leading: const Icon(Icons.motion_photos_on, color: Colors.orange),
                        title: Text(event['camera_name'] ?? event['camera_id'] ?? 'Unknown'),
                        subtitle: Text(ts != null
                            ? DateFormat('dd MMM yyyy HH:mm:ss').format(ts.toLocal())
                            : 'Unknown time'),
                        trailing: event['snapshot_url'] != null
                            ? const Icon(Icons.image, color: Colors.blue)
                            : null,
                      );
                    },
                  ),
                ),
    );
  }
}
