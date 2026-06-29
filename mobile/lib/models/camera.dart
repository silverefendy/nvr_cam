class Camera {
  final String id;
  final String name;
  final String? location;
  final String rtspMain;
  final String? rtspSub;
  final String storageDrive;
  final bool motionEnabled;
  final int retentionDays;
  final bool isActive;
  final bool isOnline;
  final int sortOrder;
  final DateTime createdAt;
  final DateTime updatedAt;

  Camera({
    required this.id,
    required this.name,
    this.location,
    required this.rtspMain,
    this.rtspSub,
    required this.storageDrive,
    required this.motionEnabled,
    required this.retentionDays,
    required this.isActive,
    required this.isOnline,
    required this.sortOrder,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Camera.fromJson(Map<String, dynamic> json) => Camera(
    id:             json['id'] as String,
    name:           json['name'] as String,
    location:       json['location'] as String?,
    rtspMain:       json['rtsp_main'] as String,
    rtspSub:        json['rtsp_sub'] as String?,
    storageDrive:   json['storage_drive'] as String,
    motionEnabled:  json['motion_enabled'] as bool? ?? false,
    retentionDays:  json['retention_days'] as int? ?? 30,
    isActive:       json['is_active'] as bool? ?? true,
    isOnline:       json['is_online'] as bool? ?? false,
    sortOrder:      json['sort_order'] as int? ?? 0,
    createdAt:      DateTime.parse(json['created_at'] as String),
    updatedAt:      DateTime.parse(json['updated_at'] as String),
  );

  Map<String, dynamic> toJson() => {
    'id': id, 'name': name, 'location': location,
    'rtsp_main': rtspMain, 'rtsp_sub': rtspSub,
    'storage_drive': storageDrive, 'motion_enabled': motionEnabled,
    'retention_days': retentionDays, 'is_active': isActive,
    'is_online': isOnline, 'sort_order': sortOrder,
    'created_at': createdAt.toIso8601String(),
    'updated_at': updatedAt.toIso8601String(),
  };
}
