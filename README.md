# QCT POSCAR generator

This repository contains the `QCT_POSCAR_generator.ipynb` notebook used to build molecule/surface initial configurations for QCT workflows, and `MACE_quick_MD_check.ipynb` for short validation MD runs on the generated POSCAR files.

The notebook is configured so you only provide VASP outputs as inputs. It reads `vasprun.xml` for the isolated molecule and the surface trajectory, then generates the molecular vibrational `.npz` cache automatically inside the notebook.

## Project layout

```text
.
├── MACE_quick_MD_check.ipynb
├── QCT_POSCAR_generator.ipynb
├── model/
│   └── mace-mh-1.model
├── inputs/
│   ├── molecule/
│   └── surface/
├── outputs/
│   └── qct_poscars/
└── requirements.txt
```

## Setup

Create and activate the local virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m ipykernel install --user --name qct-poscar-generator --display-name "Python (qct-poscar-generator)"
```

Then launch Jupyter from the repository root:

```bash
jupyter lab
```

## Expected input files

The notebook reads the following paths by default:

- `inputs/molecule/vasprun.xml`
- `inputs/surface/vasprun.xml`
- `model/mace-mh-1.model` for the quick MACE MD check notebook

The notebook also generates:

- `inputs/molecule/vibrational_modes.npz`

## Generality and assumptions

The workflow is generic with respect to the molecule and surface species: nothing is hard-coded to SO2 or to a specific slab composition.

The main assumptions are:

- `inputs/molecule/vasprun.xml` must come from an isolated-molecule calculation that contains vibrational modes (`IBRION=5` or `IBRION=6`).
- `inputs/surface/vasprun.xml` must contain an ionic trajectory that ASE can read as a sequence of frames.
- The surface normal is assumed to be along `+z`, and the molecule is launched toward `-z`.
- The molecule is treated as a free molecule for the ZPE initialization, so the vibrational modes must correspond to that isolated molecule, not to the adsorbed system.
- An optional rigid-body rotational energy can be added on top of the ZPE by setting `ROTATION_SETTINGS["temperature_K"]` in `QCT_POSCAR_generator.ipynb`. Use `0.0` or `"0K"` to disable it.
- Output POSCAR atom ordering is preserved intentionally.

Generated POSCAR files and metadata are written to:

- `outputs/qct_poscars/`

The quick MACE validation notebook writes short MD trajectories and plots under:

- `outputs/mace_md_check/`

## POSCAR generation options

`QCT_POSCAR_generator.ipynb` supports both vibrational ZPE initialization and optional rigid-body rotational excitation of the free molecule before it is placed above the surface.

- ZPE is controlled with `ZPE_SETTINGS`.
- Rotational excitation is controlled with `ROTATION_SETTINGS["temperature_K"]`.
- Set `ROTATION_SETTINGS["temperature_K"] = 0.0` or `"0K"` to deposit only the ZPE.
- Set `ROTATION_SETTINGS["temperature_K"]` to a nonzero value in kelvin to add thermal rotational energy on top of the ZPE.

## How vibrational energy is added

The vibrational initialization in `QCT_POSCAR_generator.ipynb` is based on the **harmonic normal modes of the isolated molecule**.

This means the notebook does **not** construct exact anharmonic vibrational eigenstates of the real molecule. Instead, it uses the standard harmonic approximation around the equilibrium geometry read from `inputs/molecule/vasprun.xml`.

### 1. Normal modes and frequencies

The notebook reads from the isolated-molecule `vasprun.xml`:

- the equilibrium geometry
- the normal-mode eigenvectors
- the normal-mode eigenvalues

The VASP normal-mode eigenvalues are converted to frequencies in cm<sup>-1</sup> through:

\[
\nu_k \;[\mathrm{cm}^{-1}] = \sqrt{|\lambda_k|}\times 33.35640951981521
\]

where `33.35640951981521` is the THz-to-cm<sup>-1</sup> conversion factor used in the notebook.

The angular frequency used internally is then:

\[
\omega_k = 2\pi c \nu_k
\]

with `c` in cm/s, and finally converted to fs<sup>-1</sup>.

### 2. Which vibrational level is used

The mode occupations are controlled by:

- `ZPE_SETTINGS["v_quantum"]`

If `v_quantum = None`, the notebook uses:

\[
v_k = 0
\]

for every vibrational mode, so every mode receives only its zero-point contribution.

If you provide a list such as:

```python
ZPE_SETTINGS["v_quantum"] = [0, 1, 0, 2, ...]
```

then the notebook excites each vibrational mode `k` to the harmonic quantum number `v_k` specified in that list.

### 3. Harmonic energy assigned to each mode

For each vibrational mode `k`, the target harmonic vibrational energy is:

\[
E_k = \hbar \omega_k \left(v_k + \frac{1}{2}\right)
\]

This is exactly the formula implemented in the notebook.

So:

- `v_k = 0` gives the usual zero-point energy
- `v_k = 1, 2, ...` gives higher harmonic vibrational excitation

### 4. Random phase sampling in each mode

The notebook does not put all of the energy into purely potential or purely kinetic form.

Instead, for each mode it samples a random phase:

\[
\gamma_k \sim \mathcal{U}(0, 2\pi)
\]

and distributes the mode energy between displacement and velocity consistently with a classical harmonic oscillator.

The normal-coordinate displacement amplitude is:

\[
Q_k = Q_{k,\max}\cos\gamma_k
\]

and the normal-coordinate velocity is:

\[
\dot{Q}_k = -\dot{Q}_{k,\max}\sin\gamma_k
\]

with amplitudes chosen so that the total mode energy remains equal to \(E_k\).

In the notebook, these amplitudes are built as:

\[
Q_{k,\max} = \sqrt{\frac{2E_k}{\lambda_k^{(\mathrm{cart})}}}
\]

and

\[
\dot{Q}_{k,\max} = \sqrt{\frac{2E_k}{K_{\mathrm{conv}}}}
\]

where the constants in the code convert the harmonic force constant and kinetic term into eV-consistent units.

### 5. From normal coordinates to Cartesian motion

The sampled normal-mode displacements and velocities are then transformed back to Cartesian coordinates using the mass-weighted normal-mode matrix:

\[
\Delta \mathbf{r} = \mathbf{L}\mathbf{Q}
\]

\[
\Delta \mathbf{v} = \mathbf{L}\dot{\mathbf{Q}}
\]

where:

- \(\mathbf{Q}\) contains the sampled normal-coordinate displacements
- \(\dot{\mathbf{Q}}\) contains the sampled normal-coordinate velocities
- \(\mathbf{L}\) is the mass-weighted mode matrix built from the VASP eigenvectors

The notebook then:

- adds the Cartesian displacements to the equilibrium geometry
- removes any residual center-of-mass translation
- removes any residual rigid rotation
- stores the resulting molecular velocities in ASE units

### 6. Unit convention for velocities

Internally, the sampled vibrational velocities are first built in:

\[
\text{\AA}/\mathrm{fs}
\]

They are then converted to ASE internal velocity units through:

```python
mol.set_velocities(delta_vel / units.fs)
```

This is important because ASE does not store velocities directly in VASP `Angstrom/fs` units.

### 7. What this means physically

The generated molecular vibrational state should be interpreted as:

- a **harmonic normal-mode initialization**
- based on the **isolated free-molecule Hessian**
- with the desired harmonic quantum numbers `v_k`
- but represented as a phase-randomized semiclassical displacement/velocity realization in Cartesian space

So this is appropriate if you want to initialize trajectories consistently with harmonic mode occupations, including ZPE and optional higher mode excitation.

It is **not** an exact anharmonic quantum vibrational eigenstate of the full interacting molecule/surface system.

## Quick MACE MD check

`MACE_quick_MD_check.ipynb` is intended to validate one generated POSCAR quickly before larger-scale use.

It does the following:

- reads one `outputs/qct_poscars/POSCAR_*`
- reuses the positions and velocities stored in that POSCAR
- attaches the local model `model/mace-mh-1.model`. MACE model can be downloaded here: [MACE models](https://huggingface.co/mace-foundations)
- runs a short constant-energy NVE trajectory with `VelocityVerlet`
- shows a `tqdm` progress bar during the run
- renders both static structure views and an in-notebook trajectory animation
- can optionally export the saved MD trajectory to `xyz` or `extxyz` format

Useful notebook settings:

- `CONFIG["save_xyz"] = True` enables XYZ export after the MD run.
- `CONFIG["xyz_format"]` accepts `"xyz"` or `"extxyz"`.
- `CONFIG["xyz_name"]` controls the exported file name inside `outputs/mace_md_check/`.

## GitHub notes

- The local virtual environment `.venv/` is ignored.
- Generated outputs are ignored, except for placeholder files that keep the folder structure in Git.
- Input directories are tracked but their contents are ignored by default, which avoids committing heavy or private VASP files accidentally.
- The local `model/` directory contents are ignored by default, so large model binaries are not committed accidentally.
