import 'package:json_annotation/json_annotation.dart';

part 'camera.g.dart';

@JsonSerializable()
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

  factory Camera.fromJson(Map<String, dynamic> json) => _$CameraFromJson(json);
  Map<String, dynamic> toJson() => _$CameraToJson(this);
}
