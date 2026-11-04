from pathlib import Path
from typing import Optional
import shutil
import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)
DEFAULT_DATA = DATA_DIR / "Dataset_NHANES_SANGKARA_Cuplikan.xlsx"
ACTIVE_DATA = DATA_DIR / "active_dataset.xlsx"
app = FastAPI(title="SANGKARA Python Analytics", version="1.0.0")


def read_dataset(path: Path) -> pd.DataFrame:
    try:
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        else:
            try:
                df = pd.read_excel(path, sheet_name="Data_Sampel")
            except ValueError:
                df = pd.read_excel(path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"File tidak dapat dibaca: {exc}")
    if df.empty:
        raise HTTPException(status_code=400, detail="Dataset tidak memiliki baris data.")
    return df


def first_existing(df: pd.DataFrame, names: list[str]) -> Optional[str]:
    lower = {str(c).strip().lower(): c for c in df.columns}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def numeric(df: pd.DataFrame, col: Optional[str]) -> pd.Series:
    if not col:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    return pd.to_numeric(df[col].astype(str).str.replace(",", ".", regex=False), errors="coerce")


def analyze(path: Path, dataset_name: str) -> dict:
    df = read_dataset(path)
    age_col = first_existing(df, ["Usia_tahun", "age", "ridageyr", "usia"])
    bmi_col = first_existing(df, ["BMI", "bmi", "bmxbmi"])
    sex_col = first_existing(df, ["Jenis_kelamin", "Jenis_kelamin_kode", "sex", "riagendr"])
    sys_cols = [c for c in df.columns if str(c).strip().lower().startswith("sistolik_")]
    if not sys_cols:
        c = first_existing(df, ["systolic", "sistolik", "sbp"])
        if c: sys_cols = [c]
    if not age_col:
        raise HTTPException(status_code=400, detail="Kolom usia tidak ditemukan. Gunakan nama Usia_tahun atau age.")

    work = pd.DataFrame(index=df.index)
    work["usia"] = numeric(df, age_col)
    work["bmi"] = numeric(df, bmi_col)
    if sys_cols:
        work["sistolik"] = pd.concat([numeric(df, c) for c in sys_cols], axis=1).mean(axis=1, skipna=True)
    else:
        work["sistolik"] = np.nan
    work["jenis_kelamin"] = df[sex_col].astype(str) if sex_col else "Tidak diketahui"
    elderly = work[work["usia"] >= 60].copy()
    if elderly.empty:
        raise HTTPException(status_code=400, detail="Tidak ditemukan responden berusia 60 tahun ke atas.")

    age_groups = {
        "60–69 tahun": int(((elderly.usia >= 60) & (elderly.usia <= 69)).sum()),
        "70–79 tahun": int(((elderly.usia >= 70) & (elderly.usia <= 79)).sum()),
        "80 tahun ke atas": int((elderly.usia >= 80).sum()),
    }
    # Clustering exploratory: use only complete rows and numeric features; no clinical labels.
    feature = elderly[["usia", "bmi", "sistolik"]].dropna()
    clusters = []
    if len(feature) >= 6:
        k = min(3, max(2, len(feature) // 3))
        scaled = StandardScaler().fit_transform(feature)
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(scaled)
        feature = feature.copy()
        feature["cluster"] = labels
        for label, part in feature.groupby("cluster"):
            clusters.append({
                "cluster": int(label) + 1,
                "count": int(len(part)),
                "mean_bmi": round(float(part.bmi.mean()), 2),
                "mean_systolic": round(float(part.sistolik.mean()), 2),
            })
        clusters.sort(key=lambda x: x["cluster"])

    preview = elderly.head(15).copy()
    preview = preview.rename(columns={"usia":"Usia_tahun", "bmi":"BMI", "sistolik":"Rata_sistolik_mmHg", "jenis_kelamin":"Jenis_kelamin"})
    preview = preview.replace({np.nan: None})
    records = preview.to_dict(orient="records")
    # Ensure JSON-safe native scalar values.
    records = [{k: (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)) for k,v in row.items()} for row in records]
    return {
        "dataset_name": dataset_name,
        "total_rows": int(len(df)),
        "elderly_count": int(len(elderly)),
        "mean_age": round(float(elderly.usia.mean()), 2),
        "mean_bmi": round(float(elderly.bmi.mean()), 2) if elderly.bmi.notna().any() else None,
        "mean_systolic": round(float(elderly.sistolik.mean()), 2) if elderly.sistolik.notna().any() else None,
        "missing_cells_elderly": int(elderly.isna().sum().sum()),
        "age_groups": age_groups,
        "clusters": clusters,
        "preview": records,
        "note": "Statistik dihitung dari data yang tersedia. Nilai kosong tidak dianggap nol. K-Means bersifat eksploratif dan tidak menghasilkan diagnosis atau tingkat risiko medis."
    }


@app.get("/")
def home():
    return FileResponse(BASE / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "service": "SANGKARA Python Analytics"}

@app.get("/api/analysis/summary")
def summary():
    path = ACTIVE_DATA if ACTIVE_DATA.exists() else DEFAULT_DATA
    return analyze(path, path.name)

@app.post("/api/dataset/upload")
async def upload_dataset(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise HTTPException(status_code=400, detail="Format harus CSV atau XLSX.")
    target = DATA_DIR / ("active_dataset" + suffix)
    try:
        with target.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        result = analyze(target, Path(file.filename).name)
        # Remove stale alternate extension after successful validation.
        other = DATA_DIR / ("active_dataset.csv" if suffix == ".xlsx" else "active_dataset.xlsx")
        if other.exists(): other.unlink()
        return result
    except Exception:
        if target.exists(): target.unlink()
        raise
    finally:
        await file.close()

