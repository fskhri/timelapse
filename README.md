# Aplikasi Timelapse Perekam Aktivitas Kerja

Aplikasi sederhana untuk merekam aktivitas kerja Anda dengan interval waktu tertentu (timelapse).

## Fitur

- Mengambil gambar dengan interval waktu yang dapat diatur (5 detik hingga 1 jam)
- Menampilkan preview kamera secara real-time
- Menyimpan tangkapan gambar ke direktori pilihan Anda
- Membuat video timelapse dari gambar-gambar yang diambil

## Persyaratan

- Python 3.6 atau lebih baru
- Kamera webcam

## Instalasi

1. Clone atau download repository ini
2. Install semua dependensi dengan menjalankan:

```
pip install -r requirements.txt
```

## Cara Menggunakan

1. Jalankan aplikasi:

```
python timelapse.py
```

2. Atur interval pengambilan gambar (dalam detik)
3. Pilih direktori untuk menyimpan gambar (opsional)
4. Klik "Mulai Timelapse" untuk memulai perekaman
5. Klik "Berhenti" untuk menghentikan perekaman
6. Setelah selesai, Anda dapat mengklik "Buat Video" untuk membuat video timelapse dari gambar yang diambil

## Pengaturan Tambahan

- **Interval Capture**: Waktu antara pengambilan gambar (dalam detik)
- **Direktori Output**: Lokasi penyimpanan gambar dan video 