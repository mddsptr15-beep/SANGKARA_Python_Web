# SANGKARA — Integrasi Website dengan Python

## Isi project
- `index.html`: website prototipe SANGKARA asli dengan tab tambahan Dataset & Analitik.
- `main.py`: backend FastAPI untuk membaca dataset dan menghitung statistik menggunakan Python.
- `data/Dataset_NHANES_SANGKARA_Cuplikan.xlsx`: cuplikan dataset awal 40 baris.

## Menjalankan di Windows
1. Install Python 3.10 atau lebih baru.
2. Buka folder project di VS Code.
3. Buka terminal pada folder project.
4. Buat virtual environment: `python -m venv venv`
5. Aktifkan: `venv\Scripts\activate`
6. Install library: `pip install -r requirements.txt`
7. Jalankan server: `uvicorn main:app --reload`
8. Buka browser: `http://127.0.0.1:8000`

## Fitur Python
- Membaca Excel sheet `Data_Sampel` atau CSV.
- Filter responden usia >= 60 tahun.
- Menghitung rerata usia, BMI, dan rerata pengukuran sistolik yang tersedia.
- Menghitung jumlah data kosong dan distribusi kelompok usia.
- K-Means eksploratif pada baris yang memiliki usia, BMI, dan sistolik lengkap.
- Upload dataset CSV/XLSX melalui tab Dataset & Analitik.

## Format dataset upload
Minimal harus memiliki kolom usia dengan nama `Usia_tahun` atau `age`. Kolom BMI (`BMI`/`bmi`) dan tekanan sistolik (`Sistolik_1_mmHg`, `systolic`, atau `sistolik`) bersifat opsional, tetapi dibutuhkan untuk analisis terkait. Untuk pengukuran sistolik berulang, gunakan kolom dengan awalan `Sistolik_`.

## Catatan akademik dan keselamatan
File Excel bawaan adalah cuplikan 40 baris untuk uji integrasi, bukan seluruh dataset NHANES. Sumber publik yang tercatat di workbook: CDC NHANES 2021–2023 dan salinan CSV yang dirujuk pada sheet Keterangan. Sebelum penelitian final, unduh data lengkap dari situs CDC dan cocokkan dokumentasi variabel. Hasil analisis hanya untuk eksplorasi statistik, bukan diagnosis, rekomendasi terapi, atau pengganti tenaga kesehatan. K-Means hanya menemukan kemiripan pola data, bukan kelas klinis.
