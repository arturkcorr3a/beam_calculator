from src.beam.rectangular_beam import RectangularBeam
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from indeterminatebeam import Support, DistributedLoadV

from src.reinforcement.rebar_calculator import RebarCalculator
from src.reinforcement.stirrup_calculator import StirrupCalculator
from src.reinforcement.stirrups import Stirrups
from src.report_exporter import ReportExporter

# ==============================================================================
# 1. INPUT DATA / DADOS DE ENTRADA
# ==============================================================================
length = 500  # cm (5.0 m)
width = 20    # cm (0.20 m)
height = 50   # cm (0.50 m)

concrete = Concrete.C30
steel = Steel.CA50

# Bi-apoiada (Pin supports at x = 0 cm and x = 500 cm)
a = Support(0, (1, 1, 0))
b = Support(length, (1, 1, 0))

area_m2 = (width / 100) * (height / 100)  # m²
peso_proprio_val = 25 * area_m2           # kN/m
peso_proprio = DistributedLoadV(-peso_proprio_val, (0, length))

supports = [a, b]
loads = [peso_proprio]

beam = RectangularBeam(length, width, height, concrete, steel, supports, loads)

# ==============================================================================
# 2. STRUCTURAL ANALYSIS / ESFORÇOS SOLICITANTES
# ==============================================================================
max_bending_moment_kNm = beam.get_bending_moment(return_max=True)  # kN.m
max_shear_force_kN = beam.get_shear_force(return_max=True)          # kN

gamma_f = 1.4
design_bending_moment_kNm = max_bending_moment_kNm * gamma_f        # kN.m
design_bending_moment_kNcm = design_bending_moment_kNm * 100        # kN.cm
design_shear_force_kN = max_shear_force_kN * gamma_f               # kN

# ==============================================================================
# 3. CALCULATIONS / PROCESSAMENTO DO DIMENSIONAMENTO
# ==============================================================================
stirrup_calculator = StirrupCalculator(beam, design_shear_force_kN)
stirrups = Stirrups(beam, stirrup_calculator)
calculator = RebarCalculator(beam, max_bending_moment_kNm, stirrups)
calculator.calculate()

compressed = calculator.compressed_reinforcement
tensioned = calculator.tensioned_reinforcement

# ==============================================================================
# 4. REPORT & EXPORT / APRESENTAÇÃO E EXPORTAÇÃO
# ==============================================================================
exporter = ReportExporter(
    beam=beam,
    calculator=calculator,
    stirrup_calculator=stirrup_calculator,
    stirrups=stirrups,
    max_bending_moment_kNm=max_bending_moment_kNm,
    max_shear_force_kN=max_shear_force_kN,
    gamma_f=gamma_f,
)

# Print step-by-step memory of calculation to terminal
exporter.print_to_console()

# Export reports
csv_path = exporter.export_csv("results/report-v1.csv")
pdf_path = exporter.export_pdf("results/report-v1.pdf")

print(f"[ARQUIVOS EXPORTADOS COM SUCESSO]")
print(f"  • CSV: {csv_path}")
print(f"  • PDF: {pdf_path}\n")