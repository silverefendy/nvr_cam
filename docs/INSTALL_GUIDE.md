# Panduan Instalasi dan Migrasi NVR Cam Control

Dokumen ini menjelaskan langkah-langkah untuk melakukan instalasi baru atau migrasi sistem NVR Cam Control di komputer baru (Windows/Ubuntu).

---

## 💻 1. Windows (Development / Demo)

### Persyaratan Sistem
* Windows 10/11 atau Windows Server
* Docker Desktop sudah terinstal dan berjalan

### Langkah Instalasi

1. **Clone repositori:**
   ```cmd
   git clone https://github.com/silverefendy/nvr_cam
   cd nvr_cam
   ```

2. **Setup file Environment (.env):**
   Salin file contoh konfigurasi dan ganti password default:
   ```cmd
   copy .env.example .env
   ```
   Edit file `.env` yang baru dibuat menggunakan Notepad atau VSCode:
   * Ubah `DB_PASSWORD` menjadi password kuat pilihan Anda (minimal 8 karakter).
   * Ubah `JWT_SECRET` dengan string acak panjang (minimal 32 karakter).
   * Ubah `ADMIN_PASSWORD` dengan password awal akun admin (contoh: `Admin123!`).
   * Pastikan `APP_ENV=development` untuk pengerjaan di komputer lokal.

3. **Jalankan container Docker:**
   ```cmd
   docker compose up --build -d
   ```

4. **Inisialisasi Database dan Akun Admin:**
   Tunggu kurang lebih 15-30 detik hingga PostgreSQL siap menerima koneksi, kemudian jalankan skrip pembuatan skema DB dan user admin:
   ```cmd
   docker exec -it cctv_api python3 scripts/setup_db.py
   ```

5. **Akses Dashboard:**
   Buka web browser dan akses halaman utama:
   * URL: **`http://localhost:3000`**
   * Login Default: `admin` / `Admin123!` (atau password yang Anda masukkan di `.env`).

---

## 🐧 2. Ubuntu Server (Production)

### Persyaratan Sistem
* Ubuntu Server 22.04 atau 24.04 LTS
* Memori minimal 4GB RAM
* Hard Disk Drive (HDD) khusus untuk rekaman video sudah terpasang dan di-mount.

### Langkah Instalasi

1. **Clone Repositori:**
   Kloning aplikasi ke folder `/opt/nvr_cam`:
   ```bash
   git clone https://github.com/silverefendy/nvr_cam /opt/nvr_cam
   cd /opt/nvr_cam
   ```

2. **Jalankan Skrip Instalasi Native:**
   Skrip ini akan menginstal dependencies sistem seperti Python, FFmpeg, PostgreSQL, Nginx, dan setup daemon:
   ```bash
   sudo bash scripts/install.sh
   ```

3. **Setup Environment (.env):**
   ```bash
   sudo cp /opt/nvr_cam/.env.example /opt/nvr_cam/.env
   sudo nano /opt/nvr_cam/.env
   ```
   Ubah parameter wajib:
   * `DB_PASSWORD=password_aman_db`
   * `JWT_SECRET=token_rahasia_sangat_panjang_dan_kuat`
   * `ADMIN_PASSWORD=AdminProduction123!`
   * `APP_ENV=production`

4. **Konfigurasi HDD Rekaman (Auto-Mount):**
   * Cari nama drive HDD rekaman yang terpasang (misalnya `/dev/sdb1`):
     ```bash
     lsblk
     ```
   * Buat folder mount point:
     ```bash
     sudo mkdir -p /mnt/hdd1
     ```
   * Mount drive secara manual:
     ```bash
     sudo mount /dev/sdb1 /mnt/hdd1
     ```
   * Daftarkan ke `/etc/fstab` agar otomatis ter-mount saat komputer restart:
     ```bash
     echo "/dev/sdb1 /mnt/hdd1 ext4 defaults 0 2" | sudo tee -a /etc/fstab
     ```

5. **Sesuaikan Konfigurasi Storage:**
   Buka file `/opt/nvr_cam/config/storage.yaml` dan ubah path drive ke folder HDD yang baru saja di-mount:
   ```yaml
   threshold_pct: 10
   drives:
     - path: /mnt/hdd1
       cameras: []
   ```

6. **Start dan Enable Layanan Systemd:**
   Aktifkan daemon API, recorder, motion detector, dan transcode engine:
   ```bash
   sudo systemctl start nvr-api
   sudo systemctl enable nvr-api
   ```

7. **Buat Akun Admin:**
   ```bash
   cd /opt/nvr_cam && python3 scripts/setup_db.py
   ```

8. **Akses Dashboard:**
   Buka browser dan ketik IP server Ubuntu Anda:
   * URL: **`http://<IP_SERVER_UBUNTU>:3000`**

---

## 🔄 3. Migrasi / Pindah ke Komputer Baru

Jika Anda ingin memindahkan seluruh instalasi, konfigurasi, dan data rekaman ke komputer baru, ikuti panduan berikut.

### Langkah 1: Backup dari Komputer Lama

1. **Unduh Berkas Konfigurasi:**
   Buka dashboard CamControl di komputer lama, pergi ke menu **Settings** -> tab **Backup & Restore** -> klik tombol **Download Backup Sekarang**.
   * File ini berbentuk ZIP (contoh: `nvr_config_backup_20260726.zip`) dan berisi semua pengaturan kamera (`cameras.yaml`), drive (`storage.yaml`), pengaturan sistem (`system.yaml`), dan file environment `.env`.

2. **Salin Data Rekaman Video (Opsional, file bisa berukuran besar):**
   Jika ingin memindahkan semua video rekaman CCTV lama:
   * **Menggunakan Docker:**
     ```bash
     docker cp cctv_api:/mnt/driveA ./backup_recordings
     ```
   * **Menggunakan Native (Ubuntu):**
     ```bash
     cp -r /mnt/hdd1 /backup/recordings
     ```

### Langkah 2: Restore di Komputer Baru

1. **Lakukan Instalasi Fresh:**
   Ikuti langkah instalasi fresh di atas sesuai dengan sistem operasi komputer baru (Windows Docker atau Ubuntu Native). Pastikan container atau services sudah menyala.

2. **Restore Konfigurasi via UI:**
   * Buka dashboard di komputer baru, masuk ke **Settings** -> tab **Backup & Restore**.
   * Cari section **Upload Restore Area**, drag & drop atau pilih file ZIP backup yang sudah diunduh dari komputer lama sebelumnya.
   * Klik **Restore Config**. Semua konfigurasi kamera, drive, dan settings global akan kembali dalam sekejap.

3. **Rebuild dan Restart Services:**
   * **Menggunakan Docker:**
     ```cmd
     docker compose down
     docker compose up --build -d
     ```
   * **Menggunakan Native (Ubuntu):**
     ```bash
     sudo systemctl restart nvr-api
     ```

4. **Kembalikan Berkas Rekaman (Jika melakukan salin video):**
   Salin kembali folder backup video rekaman ke path drive penyimpanan yang sesuai (misalnya `/mnt/driveA` atau `/mnt/hdd1`).
