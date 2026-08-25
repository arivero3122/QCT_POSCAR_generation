#!/usr/bin/env python3
"""Generate HPC-ready SO2/HOPG initial conditions for the 4-layer surface."""

import csv
import json
import re
from pathlib import Path

import numpy as np
from ase.io import write


NOTEBOOK = Path("QCT_POSCAR_generator.ipynb")
MOLECULE_VASPRUN = Path("inputs/molecule/SO2/vasprun_SO2.xml")
VASP_MODES_NPZ = Path("inputs/molecule/SO2/vibrational_modes-SO2.npz")
SURFACE_ROOT = Path("inputs/surface/HOPG_therm_4layers")
HPC_ROOT = Path("outputs/4_HOPG_layers")
HPC_POSCAR_SUBDIR = "poscars-rand-zpe"

TEMPERATURES = {
    "100K": "Ts100",
    "300K": "Ts300",
    "500K": "Ts500",
}
INCIDENT_ENERGIES_EV = [0.1, 0.3, 0.5, 1.0, 2.0]
N_CONFIGURATIONS = 10
MASTER_SEED = 20240331


def _load_notebook_runtime() -> dict:
    """Load reusable functions/classes from the generator notebook."""
    notebook = json.loads(NOTEBOOK.read_text())
    runtime = {"__name__": "__qct_generator_runtime__"}
    for cell_index in (2, 5, 6):
        source = "".join(notebook["cells"][cell_index]["source"])
        exec(compile(source, f"{NOTEBOOK}:cell {cell_index}", "exec"), runtime)
    return runtime


def _format_incident_energy_label(energy_eV: float) -> str:
    return f"Ei{float(energy_eV):g}"


def _numeric_poscar_key(path: Path) -> int:
    return int(path.name.split("-")[-1])


def _prepare_output_root() -> None:
    if HPC_ROOT.exists() and any(HPC_ROOT.iterdir()):
        raise FileExistsError(
            f"{HPC_ROOT} already exists and is not empty. Move or rename it before regenerating."
        )
    HPC_ROOT.mkdir(parents=True, exist_ok=True)


def _generate_batch(runtime: dict, surface_label: str, hpc_temperature_label: str, incident_energy_eV: float):
    Atoms = runtime["Atoms"]
    MoleculeRotationInitializer = runtime["MoleculeRotationInitializer"]
    MoleculeZPEInitializer = runtime["MoleculeZPEInitializer"]
    add_incident_energy = runtime["add_incident_energy"]
    choose_xy_target = runtime["choose_xy_target"]
    enforce_clearance = runtime["enforce_clearance"]
    load_modes_from_vasprun = runtime["load_modes_from_vasprun"]
    load_structure_from_vasprun = runtime["load_structure_from_vasprun"]
    load_surface_ensemble = runtime["load_surface_ensemble"]
    merge_slab_and_molecule = runtime["merge_slab_and_molecule"]
    place_molecule_above_surface = runtime["place_molecule_above_surface"]
    rotate_atoms_randomly = runtime["rotate_atoms_randomly"]
    save_modes_npz = runtime["save_modes_npz"]
    wrap_molecule_by_com_xy = runtime["wrap_molecule_by_com_xy"]

    surface_vasprun = SURFACE_ROOT / f"vasprun-{surface_label}.xml"
    if not surface_vasprun.exists():
        raise FileNotFoundError(surface_vasprun)

    molecule_eq = load_structure_from_vasprun(MOLECULE_VASPRUN)
    freqs_cm1, eigvecs_cart = load_modes_from_vasprun(MOLECULE_VASPRUN)
    save_modes_npz(VASP_MODES_NPZ, freqs_cm1, eigvecs_cart)

    rotation_initializer = MoleculeRotationInitializer(temperature_K=0.0, seed_offset=100000)
    zpe_initializer = MoleculeZPEInitializer(
        molecule_eq=molecule_eq,
        freqs_cm1=freqs_cm1,
        eigvecs_cart=eigvecs_cart,
        v_quantum=None,
        seed_offset=0,
    )
    surface_ensemble = load_surface_ensemble(
        surface_vasprun,
        fmt="vasp-xml",
        index="::10",
        keep_velocities=True,
        potim_fs=1.0,
    )

    ei_label = _format_incident_energy_label(incident_energy_eV)
    dest_dir = HPC_ROOT / ei_label / hpc_temperature_label / HPC_POSCAR_SUBDIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(MASTER_SEED)
    metadata = []
    for idx in range(N_CONFIGURATIONS):
        mol_seed = int(rng.integers(0, 2**32 - 1))
        orient_seed = int(rng.integers(0, 2**32 - 1))
        frac_xy = rng.random(2)
        snapshot_idx = int(rng.integers(0, len(surface_ensemble)))

        slab = surface_ensemble[snapshot_idx].copy()
        if slab.get_velocities() is None:
            slab.set_velocities(np.zeros((len(slab), 3)))

        mol = zpe_initializer.sample(seed=mol_seed)
        zpe_report = mol.info.get("zpe_report")
        rotate_atoms_randomly(mol, orient_seed)

        xy_target, frac_used = choose_xy_target(slab, "random", rng, frac_xy)
        place_molecule_above_surface(mol, slab, height=7.0, xy_target=xy_target)
        clearance = enforce_clearance(slab, mol, 1.3)
        wrap_molecule_by_com_xy(mol, slab.cell)
        incident_speed = add_incident_energy(
            mol,
            incident_energy_eV=incident_energy_eV,
            direction=(0.0, 0.0, -1.0),
        )

        system = merge_slab_and_molecule(slab, mol)
        if not isinstance(system, Atoms):
            raise TypeError("Generated system is not an ASE Atoms object")

        poscar_path = dest_dir / f"POSCAR-{idx + 1}"
        write(poscar_path, system, format="vasp", vasp5=True, sort=False, direct=False)

        metadata.append({
            "tag": f"config_{idx:03d}",
            "poscar": str(poscar_path),
            "source_surface_family": "HOPG_therm_4layers",
            "surface_temperature_label": surface_label,
            "hpc_temperature_label": hpc_temperature_label,
            "surface_vasprun": str(surface_vasprun),
            "incident_energy_label": ei_label,
            "snapshot_index": snapshot_idx,
            "mol_seed": mol_seed,
            "orientation_seed": orient_seed,
            "xy_fractional": frac_used.tolist(),
            "surface_distance_A": 7.0,
            "clearance_A": clearance,
            "incident_energy_eV": incident_energy_eV,
            "incident_speed_A_fs": incident_speed,
            "rotational_temperature_K": rotation_initializer.temperature_K,
            "rotational_energy_eV": 0.0,
            "zpe_target_total_eV": zpe_report["target_total_eV"],
            "zpe_modal_kinetic_eV": zpe_report["modal_kinetic_eV"],
            "zpe_modal_potential_eV": zpe_report["modal_potential_eV"],
            "zpe_modal_total_eV": zpe_report["modal_total_eV"],
            "zpe_external_leak_eV": zpe_report["external_leak_eV"],
            "zpe_mode_details": zpe_report["mode_details"],
        })

    (dest_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    return dest_dir, metadata


def main() -> None:
    runtime = _load_notebook_runtime()
    _prepare_output_root()

    index_rows = []
    job_id = 1
    for surface_label, hpc_temperature_label in TEMPERATURES.items():
        for incident_energy_eV in INCIDENT_ENERGIES_EV:
            dest_dir, metadata = _generate_batch(
                runtime=runtime,
                surface_label=surface_label,
                hpc_temperature_label=hpc_temperature_label,
                incident_energy_eV=incident_energy_eV,
            )
            for record in sorted(metadata, key=lambda item: _numeric_poscar_key(Path(item["poscar"]))):
                index_rows.append({
                    "job_id": job_id,
                    "source_surface_family": record["source_surface_family"],
                    "surface_temperature_label": record["surface_temperature_label"],
                    "hpc_temperature_label": record["hpc_temperature_label"],
                    "incident_energy_label": record["incident_energy_label"],
                    "incident_energy_eV": record["incident_energy_eV"],
                    "configuration": _numeric_poscar_key(Path(record["poscar"])),
                    "poscar": record["poscar"],
                })
                job_id += 1
            print(f"{dest_dir}: {len(metadata)} POSCAR")

    (HPC_ROOT / "index.json").write_text(json.dumps(index_rows, indent=2))
    with (HPC_ROOT / "index.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(index_rows[0]))
        writer.writeheader()
        writer.writerows(index_rows)

    poscars = sorted(HPC_ROOT.glob(f"Ei*/Ts*/{HPC_POSCAR_SUBDIR}/POSCAR-*"))
    metadata_files = sorted(HPC_ROOT.glob(f"Ei*/Ts*/{HPC_POSCAR_SUBDIR}/metadata.json"))
    if len(poscars) != len(index_rows):
        raise ValueError("POSCAR count and index row count differ")
    if len(poscars) != len(TEMPERATURES) * len(INCIDENT_ENERGIES_EV) * N_CONFIGURATIONS:
        raise ValueError("Unexpected POSCAR count")
    if len(metadata_files) != len(TEMPERATURES) * len(INCIDENT_ENERGIES_EV):
        raise ValueError("Unexpected metadata file count")

    for path in poscars:
        if not re.search(r"/Ei[^/]+/Ts\d+/poscars-rand-zpe/POSCAR-\d+$", str(path)):
            raise ValueError(f"Unexpected HPC path: {path}")

    print(f"Index rows: {len(index_rows)}")
    print(f"POSCAR files: {len(poscars)}")
    print(f"HPC output root: {HPC_ROOT}")


if __name__ == "__main__":
    main()
