# DEVIN PROMPT — nvr_cam
## Prompt Siap Pakai untuk Devin AI

**Dibuat:** 2 Juli 2026, 14:30 WIB
**Untuk:** Devin AI (devin.ai)
**Scope:** Fix semua build errors Frontend + Flutter (BUG-001 s/d BUG-009)

---

## ═══ COPY BAGIAN INI KE DEVIN ═══

---

## Konteks Proyek

Saya punya aplikasi NVR CCTV custom bernama **nvr_cam** di GitHub:
**https://github.com/silverefendy/nvr_cam**

Stack:
- **Backend:** Python 3.12 + FastAPI + PostgreSQL + SQLAlchemy + Alembic (✅ sudah selesai, tidak perlu diubah)
- **Frontend:** React 18 + TypeScript + Tailwind CSS + Vite + Zustand + TanStack Query
- **Mobile:** Flutter 3 + Riverpod + flutter_vlc_player + shared_preferences

Backend sudah beres. Yang perlu kamu fix adalah **Frontend** dan **Flutter mobile** yang gagal build.

---

## Tugas Utama

### Goal 1: Frontend `npm run build` harus berhasil (0 errors)
### Goal 2: Flutter `flutter analyze` harus 0 issues → `flutter build apk --release` berhasil

---

## Bug List yang Harus Difix (Urutan Prioritas)

---

### BUG-001 — Buat file `frontend/src/api/users.ts` (MISSING)

File ini tidak ada tapi diimport oleh `frontend/src/pages/Users/index.tsx`:
```typescript
import { usersApi } from "@/api/users"
```

Buat file `frontend/src/api/users.ts` dengan isi:
```typescript
import { apiClient } from './client'
import type { User } from "@/types"

export const usersApi = {
  list:   ()                              => apiClient.get<User[]>('/users').then(r => r.data),
  get:    (id: number)                    => apiClient.get<User>(`/users/${id}`).then(r => r.data),
  create: (data: Partial<User>)           => apiClient.post<User>('/users', data).then(r => r.data),
  update: (id: number, d: Partial<User>)  => apiClient.put<User>(`/users/${id}`, d).then(r => r.data),
  delete: (id: number)                    => apiClient.delete(`/users/${id}`),
  me:     ()                              => apiClient.get<User>('/users/me').then(r => r.data),
}
```

---

### BUG-002 — Buat file `frontend/src/api/storage.ts` (MISSING)

File ini tidak ada tapi diimport oleh `frontend/src/pages/Storage/index.tsx`:
```typescript
import { storageApi } from "@/api/storage"
```

Buat file `frontend/src/api/storage.ts` dengan isi:
```typescript
import { apiClient } from './client'
import type { StorageStatus } from "@/types"

export const storageApi = {
  getStatus:     () => apiClient.get<StorageStatus>('/storage').then(r => r.data),
  manualCleanup: () => apiClient.post('/storage/cleanup').then(r => r.data),
}
```

---

### BUG-003 — Fix `frontend/src/types/index.ts`: SystemHealth field names

File `frontend/src/pages/System/index.tsx` menggunakan field-field ini dari tipe `SystemHealth`:
- `health.cpu_usage`
- `health.ram_usage`
- `health.ram_used_gb`
- `health.ram_total_gb`
- `health.disk_usage`
- `health.disk_used_gb`
- `health.disk_total_gb`
- `health.uptime_seconds`
- `health.cameras_online`
- `health.cameras_offline`
- `health.services` (array of `{ name: string; status: string }`)

Tapi di `types/index.ts` saat ini `SystemHealth` didefinisikan dengan nama berbeda (`cpu_pct`, `ram_pct`, dst).

**Fix:** Ganti definisi `SystemHealth` di `frontend/src/types/index.ts` menjadi:
```typescript
export interface SystemHealth {
  cpu_usage: number
  ram_usage: number
  ram_used_gb: number
  ram_total_gb: number
  disk_usage: number
  disk_used_gb: number
  disk_total_gb: number
  uptime_seconds: number
  cameras_online: number
  cameras_offline: number
  camera_total: number
  services: { name: string; status: string; uptime_s?: number }[]
}
```

---

### BUG-004 — Fix `frontend/src/types/index.ts`: DriveStatus & StorageStatus field names

File `frontend/src/pages/Storage/index.tsx` menggunakan field-field ini:

Dari `DriveStatus`:
- `drive.path`
- `drive.camera_count` (bukan `cameras: string[]`)
- `drive.free_pct`
- `drive.free_bytes`
- `drive.used_bytes`
- `drive.total_bytes`

Dari `StorageStatus`:
- `storage.drives`
- `storage.threshold_pct`

**Fix:** Ganti definisi di `frontend/src/types/index.ts`:
```typescript
export interface DriveStatus {
  path: string
  total_gb: number
  used_gb: number
  free_gb: number
  free_pct: number
  total_bytes: number
  used_bytes: number
  free_bytes: number
  camera_count: number
  cameras: string[]
}

export interface StorageStatus {
  drives: DriveStatus[]
  total_tb: number
  used_tb: number
  free_tb: number
  threshold_pct: number
  estimated_days_remaining: number
}
```

---

### BUG-005 — Fix `frontend/src/types/index.ts`: User type

File `frontend/src/pages/Users/index.tsx` menggunakan:
- `user.id` sebagai `number` (bukan `string`)
- `useState<number | null>` untuk `editingId`
- `usersApi.delete(id: number)`, `usersApi.update(id: number, data)`
- Form input field `password` untuk create user

**Fix:** Update interface `User` di `frontend/src/types/index.ts`:
```typescript
export interface User {
  id: number                // UBAH dari string ke number
  username: string
  email?: string
  full_name?: string
  role: UserRole
  is_active: boolean
  last_login?: string
  created_at: string
  password?: string         // TAMBAH untuk form create
}
```

---

### BUG-006 — Fix `frontend/src/api/system.ts`: tambah alias `getHealth`

File `frontend/src/pages/System/index.tsx` memanggil `systemApi.getHealth` tapi di `system.ts` method-nya bernama `health`.

**Fix:** Update `frontend/src/api/system.ts`:
```typescript
import { apiClient } from './client'
import type { SystemHealth, StorageStatus } from "@/types"

export const systemApi = {
  health:    () => apiClient.get<SystemHealth>('/system/health').then(r => r.data),
  getHealth: () => apiClient.get<SystemHealth>('/system/health').then(r => r.data),  // alias
  storage:   () => apiClient.get<StorageStatus>('/storage').then(r => r.data),
  cleanup:   () => apiClient.post('/storage/cleanup').then(r => r.data),
}
```

---

### BUG-007 — Flutter: Fix `sharedPreferencesProvider` tidak bisa diimport

**File yang bermasalah:** `mobile/lib/main.dart`

`sharedPreferencesProvider` didefinisikan di `main.dart` sehingga screen lain tidak bisa import tanpa circular dependency.

**Fix:**
1. Buat file baru `mobile/lib/providers/shared_prefs_provider.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('SharedPreferences must be overridden in ProviderScope');
});
```

2. Update `mobile/lib/main.dart` — hapus definisi `sharedPreferencesProvider` dari sana, ganti dengan import:
```dart
import 'providers/shared_prefs_provider.dart';
```

3. Di semua screen yang pakai `sharedPreferencesProvider`, tambah import:
```dart
import '../providers/shared_prefs_provider.dart';
```

---

### BUG-008 — Flutter: Fix VLC Player constructor

**File yang bermasalah:** `mobile/lib/screens/camera_view_screen.dart` dan `mobile/lib/screens/playback_screen.dart`

Untuk `flutter_vlc_player: ^7.4.0`, constructor yang benar adalah:
```dart
// SALAH (constructor lama):
VlcPlayer(url: streamUrl)

// BENAR:
VlcPlayerController.network(
  streamUrl,
  hwAcc: HwAcc.full,
  autoPlay: true,
  options: const VlcPlayerOptions(),
)
```

Widget-nya:
```dart
VlcPlayer(
  controller: _vlcController,
  aspectRatio: 16 / 9,
  placeholder: const Center(child: CircularProgressIndicator()),
)
```

**Fix:** Cek kedua file tersebut dan update sesuai API yang benar.

---

### BUG-009 — Flutter: Fix deprecated `withOpacity()` dan buat assets directory

**Fix 1:** Global find & replace di semua file `.dart` dalam folder `mobile/lib/`:
```
CARI:    .withOpacity(
GANTI:   .withValues(alpha:
```

**Fix 2:** Buat folder dan file placeholder:
```bash
mkdir -p mobile/assets/images
# Buat file placeholder agar git track folder-nya
touch mobile/assets/images/.gitkeep
```

---

## Verifikasi Setelah Fix

Setelah semua fix selesai, jalankan perintah berikut dan pastikan output-nya clean:

### Frontend:
```bash
cd frontend
npm install
npm run build
# Expected: BUILD SUCCESS, 0 errors
```

### Flutter:
```bash
cd mobile
flutter pub get
flutter analyze
# Expected: No issues found!

flutter build apk --release
# Expected: Built build/app/outputs/flutter-apk/app-release.apk
```

---

## File yang Harus Dibuat (Baru)
1. `frontend/src/api/users.ts` — (BUG-001)
2. `frontend/src/api/storage.ts` — (BUG-002)
3. `mobile/lib/providers/shared_prefs_provider.dart` — (BUG-007)
4. `mobile/assets/images/.gitkeep` — (BUG-009)

## File yang Harus Dimodifikasi (Edit)
1. `frontend/src/types/index.ts` — (BUG-003, BUG-004, BUG-005)
2. `frontend/src/api/system.ts` — (BUG-006)
3. `mobile/lib/main.dart` — (BUG-007)
4. `mobile/lib/screens/camera_view_screen.dart` — (BUG-008)
5. `mobile/lib/screens/playback_screen.dart` — (BUG-008)
6. Semua file `.dart` yang pakai `withOpacity()` — (BUG-009)

## File yang TIDAK BOLEH Diubah
- Semua file di `backend/` — backend sudah beres
- `frontend/src/pages/` — jangan ubah logic pages, hanya fix type errors jika perlu
- `mobile/pubspec.yaml` — sudah benar
- `config/`, `scripts/` — infrastructure files

---

## Catatan Penting untuk Devin

1. **Jangan ubah backend** — Python/FastAPI backend sudah selesai dan semua test passing
2. **Jangan tambah dependencies baru** di package.json atau pubspec.yaml tanpa alasan kuat
3. **Setelah fix, commit dengan pesan yang jelas** per bug yang difix, contoh:
   - `fix(frontend): add missing users.ts and storage.ts API modules`
   - `fix(types): sync SystemHealth field names with System page`
   - `fix(flutter): extract sharedPreferencesProvider to separate file`
4. **Push ke branch `main`** langsung (tidak perlu PR)
5. **Update PROGRESS.md** setelah selesai — ubah status BUG-001 s/d BUG-009 menjadi ✅ dan tambah timestamp selesainya

---

## ═══ AKHIR PROMPT DEVIN ═══

---

*File ini dibuat: 2 Juli 2026, 14:30 WIB*
*Repo: https://github.com/silverefendy/nvr_cam*
