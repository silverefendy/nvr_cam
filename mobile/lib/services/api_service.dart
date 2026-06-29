import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/camera.dart';

class ApiService {
  late Dio _dio;
  String? _baseUrl;

  ApiService() {
    _dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
    ));
  }

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _baseUrl = prefs.getString('serverUrl');
    if (_baseUrl != null) {
      _dio.options.baseUrl = _baseUrl!;
    }
  }

  Future<void> setServerUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('serverUrl', url);
    _baseUrl = url;
    _dio.options.baseUrl = url;
  }

  Future<void> setAuthToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('authToken', token);
    _dio.options.headers['Authorization'] = 'Bearer $token';
  }

  Future<void> clearAuth() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('authToken');
    _dio.options.headers.remove('Authorization');
  }

  // Auth
  Future<bool> login(String username, String password) async {
    try {
      final response = await _dio.post('/api/v1/auth/login', data: {
        'username': username,
        'password': password,
      });

      if (response.statusCode == 200) {
        final token = response.data['access_token'];
        await setAuthToken(token);
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  // Cameras
  Future<List<Camera>> getCameras() async {
    try {
      final response = await _dio.get('/api/v1/config/cameras');
      if (response.statusCode == 200) {
        final cameras = response.data['data']['cameras'] as List;
        return cameras.map((c) => Camera.fromJson(c)).toList();
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  Future<Camera?> getCamera(String id) async {
    try {
      final response = await _dio.get('/api/v1/config/cameras/$id');
      if (response.statusCode == 200) {
        return Camera.fromJson(response.data['data']);
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  // Stream URL
  String getStreamUrl(String cameraId) {
    return '$_baseUrl/api/v1/stream/live/$cameraId';
  }

  // Snapshot URL
  String getSnapshotUrl(String cameraId) {
    return '$_baseUrl/api/v1/stream/snapshot/$cameraId';
  }

  // System status
  Future<Map<String, dynamic>> getSystemStatus() async {
    try {
      final response = await _dio.get('/api/v1/system/health');
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return {};
    } catch (e) {
      return {};
    }
  }

  // Events
  Future<List<Map<String, dynamic>>> getEvents({int limit = 50}) async {
    try {
      final response = await _dio.get('/api/v1/events', queryParameters: {'limit': limit});
      if (response.statusCode == 200) {
        final data = response.data;
        if (data is List) return List<Map<String, dynamic>>.from(data);
        if (data['data'] is List) return List<Map<String, dynamic>>.from(data['data']);
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  // Recordings
  Future<List<Map<String, dynamic>>> getRecordings({
    required String cameraId,
    required DateTime dateFrom,
    required DateTime dateTo,
  }) async {
    try {
      final response = await _dio.get('/api/v1/recordings', queryParameters: {
        'camera_id': cameraId,
        'date_from': dateFrom.toIso8601String(),
        'date_to': dateTo.toIso8601String(),
      });
      if (response.statusCode == 200) {
        final data = response.data;
        if (data is List) return List<Map<String, dynamic>>.from(data);
        if (data['data'] is List) return List<Map<String, dynamic>>.from(data['data']);
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  String getRecordingUrl(String recordingId) {
    return '$_baseUrl/api/v1/recordings/$recordingId/play';
  }
}
