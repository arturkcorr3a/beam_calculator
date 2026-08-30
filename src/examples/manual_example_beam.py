from datetime import datetime

from src.elements.rectangular_beam import RectangularBeam
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from indeterminatebeam import Support, DistributedLoadV

from src.reinforcement.rebar_calculator import RebarCalculator
from src.reinforcement.stirrup_calculator import StirrupCalculator
from src.reinforcement.stirrups import Stirrups
from src.loading.forces import LOAD_FACTOR, design_effort_elu as design_effort_elu
from src.gui.report_exporter import ReportExporter

# ==============================================================================
# 1. INPUT DATA / DADOS DE ENTRADA
# ==============================================================================
span1 = 621.5  # cm
span2 = 620    # cm
span3 = 781.5  # cm
length = span1 + span2 + span3  # cm

width = 19    # cm 
height = 65   # cm 

concrete = Concrete.C40
steel = Steel.CA50

# Contínua (sem considerações de rigidez)
fixed = (1, 1, 0)
p1 = Support(0, fixed)
p2 = Support(span1, fixed)
p3 = Support(span1 + span2, fixed)
p4 = Support(length, fixed)

# Carregamento (sinal negativo pq é para baixo)
load1 = -15.710  # kN/m -20.3 #
load2 = -14.479  # kN/m -20.3 #
load3 = -31.672  # kN/m -20.3 # 

load_span1 = DistributedLoadV(load1, (0, span1))
load_span2 = DistributedLoadV(load2, (span1, span1 + span2))
load_span3 = DistributedLoadV(load3, (span1 + span2, length))

supports = [p1, p2, p3, p4]
loads = [load_span1, load_span2, load_span3]

beam = RectangularBeam(length, width, height, concrete, steel, supports, loads)

# ==============================================================================
# 2. STRUCTURAL ANALYSIS / ESFORÇOS SOLICITANTES
# ==============================================================================
max_bending_moment = beam.get_bending_moment(return_max=True)    # kN.m
max_shear_force = beam.get_shear_force(return_max=True)          # kN

design_bending_moment = design_effort_elu(max_bending_moment)         # kN.m
design_shear_force = design_effort_elu(max_shear_force)               # kN

# ==============================================================================
# 3. CALCULATIONS / PROCESSAMENTO DO DIMENSIONAMENTO
# ==============================================================================
stirrup_calculator = StirrupCalculator(beam, design_shear_force)
stirrups = Stirrups(beam, stirrup_calculator)

calculator = RebarCalculator(beam, max_bending_moment, stirrups)
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
    max_bending_moment_kNm=max_bending_moment,
    max_shear_force_kN=max_shear_force,
    gamma_f=LOAD_FACTOR,
)

# Print step-by-step memory of calculation to terminal
exporter.print_to_console()

# Export reports
today = datetime.now().strftime("%b-%d").lower()
csv_path = exporter.export_csv(f"results/{today}/report.csv")
pdf_path = exporter.export_pdf(f"results/{today}/report.pdf")

print("[ARQUIVOS EXPORTADOS COM SUCESSO]")
print(f"  • CSV: {csv_path}")
print(f"  • PDF: {pdf_path}\n")