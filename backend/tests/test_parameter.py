from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from sentinel.parameter import KODE_ATURAN, muat_parameter

PARAMETER_REPO = Path(__file__).resolve().parents[2] / "config" / "parameter.yaml"


@pytest.fixture
def data_valid() -> dict:
    with PARAMETER_REPO.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _tulis(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "parameter.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_file_parameter_repo_valid_dan_berisi_default_roadmap():
    p = muat_parameter(PARAMETER_REPO)

    assert p.kapasitas.fisioterapi_sesi_per_terapis_per_hari == 8
    assert p.kapasitas.hemodialisa_durasi_sesi_jam == 4
    assert p.kapasitas.hemodialisa_shift_per_hari == 3
    assert p.kewajaran.toleransi_harga_di_atas_acuan_persen == 10
    assert p.kewajaran.alat_bantu_dengar_masa_penggantian_tahun == 5
    assert p.kewajaran.alat_bantu_dengar_per_telinga is True
    assert p.perbandingan.ambang_robust_z == 3
    assert p.sensor.toleransi_selisih_jam_mesin_persen == 10
    assert set(p.bobot_aturan) == set(KODE_ATURAN)
    assert sum(p.bobot_aturan.values()) == 100


def test_default_path_dibaca_dari_settings():
    assert muat_parameter() == muat_parameter(PARAMETER_REPO)


def test_kunci_tidak_dikenal_ditolak(tmp_path, data_valid):
    data_valid["kapasitas"]["fisioterapi_sesi_per_terapis_perhari"] = 8  # salah ketik

    with pytest.raises(ValidationError):
        muat_parameter(_tulis(tmp_path, data_valid))


def test_parameter_wajib_tidak_boleh_hilang(tmp_path, data_valid):
    del data_valid["sensor"]

    with pytest.raises(ValidationError):
        muat_parameter(_tulis(tmp_path, data_valid))


def test_nilai_kapasitas_harus_positif(tmp_path, data_valid):
    data_valid["kapasitas"]["hemodialisa_shift_per_hari"] = 0

    with pytest.raises(ValidationError):
        muat_parameter(_tulis(tmp_path, data_valid))


def test_bobot_aturan_harus_lengkap(tmp_path, data_valid):
    del data_valid["bobot_aturan"]["SEN-01"]

    with pytest.raises(ValidationError, match="belum lengkap"):
        muat_parameter(_tulis(tmp_path, data_valid))


def test_bobot_aturan_tidak_boleh_kode_asing(tmp_path, data_valid):
    data_valid["bobot_aturan"]["XXX-99"] = 0

    with pytest.raises(ValidationError, match="tidak dikenal"):
        muat_parameter(_tulis(tmp_path, data_valid))


def test_jumlah_bobot_harus_100(tmp_path, data_valid):
    data_valid["bobot_aturan"]["KAP-01"] += 1

    with pytest.raises(ValidationError, match="jumlah bobot"):
        muat_parameter(_tulis(tmp_path, data_valid))


def test_bobot_tidak_boleh_negatif(tmp_path, data_valid):
    data_valid["bobot_aturan"]["KAP-01"] -= 20
    data_valid["bobot_aturan"]["KAP-02"] += 20

    with pytest.raises(ValidationError, match="negatif"):
        muat_parameter(_tulis(tmp_path, data_valid))
