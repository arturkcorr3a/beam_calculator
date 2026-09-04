import csv
import os
from collections import Counter

from src.elements.rectangular_beam import RectangularBeam
from src.properties.section_properties_calculator import SectionPropertiesCalculator
from src.reinforcement.rebar_calculator import RebarCalculator
from src.reinforcement.stirrup_calculator import StirrupCalculator
from src.reinforcement.stirrups import Stirrups

# FIXME This was AI-generated code to make quick validations, at the end, calculation will be more complex and this will probably be broken. At that point, refactor this without AI
class ReportExporter:
    """
    Exports the beam calculation and design report to CSV and PDF formats.
    """

    def __init__(
        self,
        beam: RectangularBeam,
        calculator: RebarCalculator,
        stirrup_calculator: StirrupCalculator,
        stirrups: Stirrups,
        max_bending_moment_kNm: float,
        max_shear_force_kN: float,
        gamma_f: float = 1.4,
    ):
        self.beam = beam
        self.calculator = calculator
        self.stirrup_calculator = stirrup_calculator
        self.stirrups = stirrups
        self.max_bending_moment_kNm = max_bending_moment_kNm
        self.max_shear_force_kN = max_shear_force_kN
        self.gamma_f = gamma_f

        self.concrete = beam.concrete
        self.steel = beam.steel
        self.tensioned = calculator.tensioned_reinforcement
        self.compressed = calculator.compressed_reinforcement

        # Derived values
        self.design_bending_moment_kNm = max_bending_moment_kNm * gamma_f
        self.design_bending_moment_kNcm = self.design_bending_moment_kNm * 100
        self.design_shear_force_kN = max_shear_force_kN * gamma_f

        # Calculate provided areas
        self.total_as_provided = sum(
            d.area_cm2 for layer in self.tensioned.chosen_bars for d in layer
        )
        self.total_as2_provided = sum(
            d.area_cm2 for layer in self.compressed.chosen_bars for d in layer
        ) if (self.compressed.is_chosen and not self.calculator.is_singly_reinforced) else 0.0

        self.actual_stirrup_ratio = Stirrups.calculate_ratio(self.stirrups.diameter, self.stirrups.spacing)

    def _get_structured_data(self):
        """Builds a structured dictionary of all calculation steps."""
        # Longitudinal bars summary string
        tension_bars_list = [d.diameter_mm for layer in self.tensioned.chosen_bars for d in layer]
        tension_bars_count = Counter(tension_bars_list)
        tension_bars_str = " + ".join(
            f"{count} Φ {int(d) if float(d).is_integer() else d} mm"
            for d, count in sorted(tension_bars_count.items(), key=lambda item: item[0], reverse=True)
        )

        compression_bars_str = "N/A"
        if self.compressed.is_chosen and not self.calculator.is_singly_reinforced:
            comp_bars_list = [d.diameter_mm for layer in self.compressed.chosen_bars for d in layer]
            comp_bars_count = Counter(comp_bars_list)
            compression_bars_str = " + ".join(
                f"{count} Φ {int(d) if float(d).is_integer() else d} mm"
                for d, count in sorted(comp_bars_count.items(), key=lambda item: item[0], reverse=True)
            )

        stirrup_str = f"2 ramos Φ {self.stirrups.diameter * 10:.1f} mm c/ {self.stirrups.spacing:.1f} cm"

        return [
            # Group, Parameter, Value, Unit, Description / Status
            ("METADADOS", "Norma de Referência", "ABNT NBR 6118:2023", "-", "Dimensionamento de Estruturas de Concreto"),
            ("METADADOS", "Elemento Estrutural", "Viga Retangular Bi-apoiada", "-", "-"),
            
            ("1. GEOMETRIA E MATERIAIS", "Comprimento do Vão (L)", f"{self.beam.length:.1f}", "cm", f"{self.beam.length/100:.2f} m"),
            ("1. GEOMETRIA E MATERIAIS", "Largura da Seção (bw)", f"{self.beam.width:.1f}", "cm", "-"),
            ("1. GEOMETRIA E MATERIAIS", "Altura da Seção (h)", f"{self.beam.height:.1f}", "cm", "-"),
            ("1. GEOMETRIA E MATERIAIS", "Cobrimento Nominal (c_nom)", f"{self.beam.nominal_covering:.1f}", "cm", "Classe de Agressividade II"),
            ("1. GEOMETRIA E MATERIAIS", "Área da Seção Bruta (Ac)", f"{self.beam.width * self.beam.height:.1f}", "cm²", "-"),
            ("1. GEOMETRIA E MATERIAIS", "Classe do Concreto", f"{self.concrete.name}", "-", f"fck = {self.concrete.value} MPa"),
            ("1. GEOMETRIA E MATERIAIS", "Resistência de Cálculo fcd", f"{self.concrete.fcd:.4f}", "kN/cm²", f"{self.concrete.value / 1.4:.2f} MPa"),
            ("1. GEOMETRIA E MATERIAIS", "Resistência à Tração Média fctm", f"{self.concrete.fct_m * 10:.2f}", "MPa", f"{self.concrete.fct_m:.4f} kN/cm²"),
            ("1. GEOMETRIA E MATERIAIS", "Resistência à Tração de Cálculo fctd", f"{self.concrete.fctd:.4f}", "kN/cm²", "-"),
            ("1. GEOMETRIA E MATERIAIS", "Tensão Uniforme do Concreto sig_cd", f"{self.concrete.calculate_uniform_stress():.4f}", "kN/cm²", f"alpha_c={self.concrete.alpha_c:.2f}, lambda={self.concrete.lambda_c:.2f}"),
            ("1. GEOMETRIA E MATERIAIS", "Classe do Aço", f"{self.steel.name}", "-", f"fyk = {self.steel.value * 10} MPa"),
            ("1. GEOMETRIA E MATERIAIS", "Resistência de Cálculo do Aço fyd", f"{self.steel.fyd:.4f}", "kN/cm²", f"{self.steel.fyd * 10:.2f} MPa"),
            ("1. GEOMETRIA E MATERIAIS", "Módulo de Elasticidade do Aço Es", f"{self.steel.elastic_modulus:.0f}", "MPa", "-"),

            ("2. ESFORÇOS SOLICITANTES", "Momento Fletor Característico (Mk)", f"{self.max_bending_moment_kNm:.3f}", "kN.m", f"{self.max_bending_moment_kNm * 100:.2f} kN.cm"),
            ("2. ESFORÇOS SOLICITANTES", "Coeficiente de Ponderação (gamma_f)", f"{self.gamma_f:.2f}", "-", "-"),
            ("2. ESFORÇOS SOLICITANTES", "Momento Fletor de Projeto (Md)", f"{self.design_bending_moment_kNm:.3f}", "kN.m", f"{self.design_bending_moment_kNcm:.2f} kN.cm"),
            ("2. ESFORÇOS SOLICITANTES", "Força Cortante Característica (Vk)", f"{self.max_shear_force_kN:.3f}", "kN", "-"),
            ("2. ESFORÇOS SOLICITANTES", "Força Cortante de Projeto (Vsd)", f"{self.design_shear_force_kN:.3f}", "kN", "-"),

            ("3. DIMENSIONAMENTO À FLEXÃO", "Altura Útil Adotada (d)", f"{self.calculator.d:.2f}", "cm", f"d/h = {self.calculator.d / self.beam.height:.3f}"),
            ("3. DIMENSIONAMENTO À FLEXÃO", "Profundidade Limite y_max", f"{self.calculator.max_y:.2f}", "cm", "Limite Domínio 3 / x/d <= 0.45"),
            ("3. DIMENSIONAMENTO À FLEXÃO", "Momento Limite Armadura Simples (Md,lim)", f"{self.calculator.max_bending_moment:.2f}", "kN.cm", f"{self.calculator.max_bending_moment/100:.2f} kN.m"),
            ("3. DIMENSIONAMENTO À FLEXÃO", "Tipo de Armadura", "SIMPLES" if self.calculator.is_singly_reinforced else "DUPLA", "-", "OK" if self.calculator.is_singly_reinforced else "Requer As2"),
            ("3. DIMENSIONAMENTO À FLEXÃO", "Profundidade Linha Neutra Equiv. (y)", f"{self.calculator.actual_y:.3f}" if self.calculator.is_singly_reinforced else f"{self.calculator.max_y:.3f}", "cm", f"x = {(self.calculator.actual_y if self.calculator.is_singly_reinforced else self.calculator.max_y)/self.concrete.lambda_c:.3f} cm"),
            ("3. DIMENSIONAMENTO À FLEXÃO", "Área de Aço Calculada (As,calc)", f"{self.calculator.as1:.3f}", "cm²", "-"),
            ("3. DIMENSIONAMENTO À FLEXÃO", "Área de Aço Mínima (As,min)", f"{self.calculator.min_tension_rebar_area:.3f}", "cm²", f"Taxa mín = {100 * self.calculator.min_tension_rebar_area / (self.beam.width * self.beam.height):.3f}%"),
            ("3. DIMENSIONAMENTO À FLEXÃO", "Área de Aço Máxima (As,max)", f"{self.calculator.max_rebar_area:.3f}", "cm²", "4% Ac"),
            ("3. DIMENSIONAMENTO À FLEXÃO", "Área de Aço de Tração Requerida (As,nec)", f"{self.calculator.tensioned_rebar_area:.3f}", "cm²", "-"),
            ("3. DIMENSIONAMENTO À FLEXÃO", "Área de Aço de Tração Efetiva (As,efet)", f"{self.total_as_provided:.3f}", "cm²", "ATENDE" if self.total_as_provided >= self.calculator.tensioned_rebar_area else "NÃO ATENDE"),
            ("3. DIMENSIONAMENTO À FLEXÃO", "Barras Adotadas (Tração)", tension_bars_str, "-", f"Distribuídas em {len([l for l in self.tensioned.chosen_bars if l])} camadas"),

            ("4. CISALHAMENTO (ESTRIBOS)", "Resistência da Biela Comprimida (VRd2)", f"{self.stirrup_calculator.compressed_strut_resistance:.2f}", "kN", "OK (Vsd <= VRd2)" if self.design_shear_force_kN <= self.stirrup_calculator.compressed_strut_resistance else "FALHA"),
            ("4. CISALHAMENTO (ESTRIBOS)", "Contribuição do Concreto (Vc)", f"{self.stirrup_calculator.concrete_contribution:.2f}", "kN", "-"),
            ("4. CISALHAMENTO (ESTRIBOS)", "Esforço Resistido por Estribos (Vsw)", f"{self.stirrup_calculator.required_contribution:.2f}", "kN", "-"),
            ("4. CISALHAMENTO (ESTRIBOS)", "Taxa de Estribos Requerida (Asw/s)", f"{self.stirrup_calculator.required_ratio:.4f}", "cm²/cm", f"{self.stirrup_calculator.required_ratio * 100:.2f} cm²/m"),
            ("4. CISALHAMENTO (ESTRIBOS)", "Taxa Mínima de Estribos (Asw/s,min)", f"{self.stirrup_calculator.minimum_ratio:.4f}", "cm²/cm", f"{self.stirrup_calculator.minimum_ratio * 100:.2f} cm²/m"),
            ("4. CISALHAMENTO (ESTRIBOS)", "Espaçamento Máximo (s_max)", f"{self.stirrup_calculator.max_spacing:.1f}", "cm", "-"),
            ("4. CISALHAMENTO (ESTRIBOS)", "Estribo Adotado", stirrup_str, "-", "-"),
            ("4. CISALHAMENTO (ESTRIBOS)", "Taxa Efetiva de Estribos (Asw/s,efet)", f"{self.actual_stirrup_ratio:.4f}", "cm²/cm", "ATENDE" if self.actual_stirrup_ratio >= self.stirrup_calculator.required_ratio else "NÃO ATENDE"),

            ("5. RESUMO EXECUTIVO", "Armadura Longitudinal Inferior", tension_bars_str, "-", f"As = {self.total_as_provided:.2f} cm²"),
            ("5. RESUMO EXECUTIVO", "Armadura Longitudinal Superior", compression_bars_str, "-", f"As' = {self.total_as2_provided:.2f} cm²" if self.total_as2_provided > 0 else "Porta-estribos"),
            ("5. RESUMO EXECUTIVO", "Armadura Transversal (Estribos)", stirrup_str, "-", f"Asw/s = {self.actual_stirrup_ratio * 100:.2f} cm²/m"),
        ]

    def export_csv(self, filename: str = "relatorio_viga.csv") -> str:
        """Exports the calculation data to a CSV file."""
        data = self._get_structured_data()
        filepath = os.path.abspath(filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.writer(csvfile, delimiter=";")
            writer.writerow(["Etapa / Categoria", "Parâmetro", "Valor", "Unidade", "Detalhes / Status"])
            for row in data:
                writer.writerow(row)
        return filepath

    def export_pdf(self, filename: str = "relatorio_viga.pdf") -> str:
        """
        Exports the calculation report to a clean, professionally formatted PDF file
        using matplotlib (standard vector PDF backend).
        """
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages

        filepath = os.path.abspath(filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = self._get_structured_data()

        with PdfPages(filepath) as pdf:
            # Figure setup - Standard A4 (8.27 x 11.69 inches)
            fig, ax = plt.subplots(figsize=(8.27, 11.69), dpi=300)
            ax.axis("off")

            # Document Title & Header Banner
            plt.text(0.5, 0.96, "MEMÓRIA DE CÁLCULO E DIMENSIONAMENTO DE VIGA", ha="center", va="top", fontsize=13, fontweight="bold", color="#1a202c", transform=ax.transAxes)
            plt.text(0.5, 0.935, "Conformidade com a ABNT NBR 6118:2023 | Concreto Armado", ha="center", va="top", fontsize=9.5, style="italic", color="#4a5568", transform=ax.transAxes)
            plt.plot([0.04, 0.96], [0.915, 0.915], color="#2b6cb0", lw=2, transform=ax.transAxes)

            # Build table data for matplotlib Table
            table_rows = []
            row_colors = []
            
            prev_group = ""
            for group, param, val, unit, desc in data:
                if group != prev_group and group != "METADADOS":
                    # Section Header Row
                    table_rows.append([f"{group}", "", "", ""])
                    row_colors.append(["#ebf8ff", "#ebf8ff", "#ebf8ff", "#ebf8ff"])
                    prev_group = group

                if group == "METADADOS":
                    continue

                table_rows.append([param, val, unit, desc])
                # Alternate row coloring
                if len(table_rows) % 2 == 0:
                    row_colors.append(["#ffffff", "#ffffff", "#ffffff", "#ffffff"])
                else:
                    row_colors.append(["#f7fafc", "#f7fafc", "#f7fafc", "#f7fafc"])

            # Render Table
            table = ax.table(
                cellText=table_rows,
                colLabels=["Parâmetro", "Valor", "Unid.", "Observações / Verificação"],
                cellColours=row_colors,
                colWidths=[0.42, 0.16, 0.10, 0.32],
                loc="upper center",
                bbox=[0.04, 0.04, 0.92, 0.86]
            )

            table.auto_set_font_size(False)
            table.set_fontsize(7.2)

            # Styling table cells
            for (r, c), cell in table.get_celld().items():
                cell.set_edgecolor("#cbd5e0")
                cell.set_linewidth(0.5)
                if r == 0:
                    # Table header
                    cell.set_facecolor("#2b6cb0")
                    cell.set_text_props(color="white", fontweight="bold", fontsize=7.8)
                else:
                    row_data = table_rows[r - 1]
                    if row_data[1] == "" and row_data[2] == "" and row_data[3] == "":
                        # Group header
                        cell.set_text_props(fontweight="bold", color="#2c5282")
                    else:
                        # Alignment
                        if c == 1:
                            cell.set_text_props(ha="center")
                        elif c == 2:
                            cell.set_text_props(ha="center")
                        
                        # Status highlights
                        if "ATENDE" in row_data[3] or "OK" in row_data[3]:
                            if c == 3:
                                cell.set_text_props(color="#22543d", fontweight="bold")
                        elif "FALHA" in row_data[3] or "NÃO ATENDE" in row_data[3]:
                            if c == 3:
                                cell.set_text_props(color="#742a2a", fontweight="bold")

            # Footer
            plt.text(0.5, 0.015, "Relatório gerado automaticamente por Beam Calculator - UFRGS TCC", ha="center", va="bottom", fontsize=7.5, color="#718096", transform=ax.transAxes)

            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

        return filepath

    def print_to_console(self) -> None:
        """
        Prints the complete step-by-step beam calculation and design report
        neatly to the console.
        """
        W = 75  # Banner width
        sep_major = "=" * W
        sep_minor = "-" * W

        print("\n" + sep_major)
        print(" " * 18 + "MEMÓRIA DE CÁLCULO E DIMENSIONAMENTO DE VIGA")
        print(" " * 22 + "ABNT NBR 6118:2023 - CONCRETO ARMADO")
        print(sep_major)

        # --- PASSO 1: DADOS GERAIS ---
        print(f"\n[PASSO 1] CARACTERÍSTICAS DA SEÇÃO E MATERIAIS")
        print(sep_minor)
        print(f"  • Vão da viga (L)          : {self.beam.length:.1f} cm ({self.beam.length/100:.2f} m)")
        print(f"  • Largura da seção (bw)    : {self.beam.width:.1f} cm")
        print(f"  • Altura da seção (h)      : {self.beam.height:.1f} cm")
        print(f"  • Cobrimento nominal (c_nom): {self.beam.nominal_covering:.1f} cm (Classe de Agressividade II)")
        print(f"  • Área da seção bruta (Ac) : {self.beam.width * self.beam.height:.1f} cm² ({(self.beam.width/100)*(self.beam.height/100):.4f} m²)")
        print(f"  • Concreto                 : {self.concrete.name} (fck = {self.concrete.value} MPa)")
        print(f"    - fcd = fck / 1.4        : {self.concrete.fcd:.4f} kN/cm² ({self.concrete.value/1.4:.2f} MPa)")
        print(f"    - fctm                   : {self.concrete.fct_m * 10:.2f} MPa ({self.concrete.fct_m:.4f} kN/cm²)")
        print(f"    - fctd = 0.7*fctm / 1.4  : {self.concrete.fctd:.4f} kN/cm²")
        print(f"    - Tensão uniforme (sig_cd): {self.concrete.calculate_uniform_stress():.4f} kN/cm² (alpha_c={self.concrete.alpha_c:.2f}, lambda={self.concrete.lambda_c:.2f})")
        print(f"  • Aço                      : {self.steel.name} (fyk = {self.steel.value} kN/cm² / {self.steel.value * 10} MPa)")
        print(f"    - fyd = fyk / 1.15       : {self.steel.fyd:.4f} kN/cm² ({self.steel.fyd * 10:.2f} MPa)")
        print(f"    - Módulo de elasticidade : {self.steel.elastic_modulus:.0f} MPa")

        # --- PASSO 2: ESFORÇOS SOLICITANTES ---
        print(f"\n[PASSO 2] CARGAS E ESFORÇOS SOLICITANTES DE CÁLCULO")
        print(sep_minor)
        print(f"  • Momento fletor carac. Mk : {self.max_bending_moment_kNm:.3f} kN.m ({self.max_bending_moment_kNm * 100:.2f} kN.cm)")
        print(f"  • Momento fletor de proj. Md: {self.design_bending_moment_kNm:.3f} kN.m ({self.design_bending_moment_kNcm:.2f} kN.cm) [gamma_f = {self.gamma_f}]")
        print(f"  • Cortante característico Vk: {self.max_shear_force_kN:.3f} kN")
        print(f"  • Cortante de projeto Vsd  : {self.design_shear_force_kN:.3f} kN [gamma_f = {self.gamma_f}]")

        # --- PASSO 3: DIMENSIONAMENTO À FLEXÃO ---
        print(f"\n[PASSO 3] DIMENSIONAMENTO DA ARMADURA LONGITUDINAL (FLEXÃO)")
        print(sep_minor)
        print(f"  3.1. Altura Útil e Limites de Deformação:")
        print(f"       - Altura útil final (d) : {self.calculator.d:.2f} cm")
        print(f"       - Altura útil d/h       : {self.calculator.d / self.beam.height:.3f}")
        print(f"       - Profundidade máx. (y_max): {self.calculator.max_y:.2f} cm (Limite Domínio 3 / Ductilidade: x/d <= 0.45)")
        print(f"       - Momento máximo simples: {self.calculator.max_bending_moment:.2f} kN.cm ({self.calculator.max_bending_moment/100:.2f} kN.m)")

        if self.calculator.is_singly_reinforced:
            print(f"       -> Classificação        : ARMADURA SIMPLES (Md = {self.design_bending_moment_kNcm:.2f} <= Md,lim = {self.calculator.max_bending_moment:.2f} kN.cm)")
            print(f"       - Linha neutra equiv. y : {self.calculator.actual_y:.3f} cm (x = {self.calculator.actual_y / self.concrete.lambda_c:.3f} cm, x/d = {(self.calculator.actual_y / self.concrete.lambda_c)/self.calculator.d:.3f})")
        else:
            print(f"       -> Classificação        : ARMADURA DUPLA (Md = {self.design_bending_moment_kNcm:.2f} > Md,lim = {self.calculator.max_bending_moment:.2f} kN.cm)")
            print(f"       - Momento residual dMd  : {self.calculator.calculate_delta_bending_moment():.2f} kN.cm")
            print(f"       - Tensão arm. compr. s2 : {self.calculator.corrected_sigma_s2:.3f} kN/cm²")

        print(f"\n  3.2. Área de Aço Necessária:")
        print(f"       - As,calculado          : {self.calculator.as1:.3f} cm²")
        print(f"       - As,mínimo (NBR 6118)  : {self.calculator.min_tension_rebar_area:.3f} cm² (0.15% Ac = {0.0015 * self.beam.width * self.beam.height:.3f} cm²)")
        print(f"       - As,máximo permitido   : {self.calculator.max_rebar_area:.3f} cm² (4% Ac)")
        print(f"       -> As,tração de projeto : {self.calculator.tensioned_rebar_area:.3f} cm²")

        if not self.calculator.is_singly_reinforced:
            print(f"       -> As,compressão projeto: {self.calculator.compressed_rebar_area:.3f} cm²")

        print(f"\n  3.3. Detalhamento da Armadura Longitudinal de Tração:")
        for i, layer in enumerate(self.tensioned.chosen_bars):
            if layer:
                layer_count = Counter([d.diameter_mm for d in layer])
                layer_area = sum(d.area_cm2 for d in layer)
                formatted_bars = " + ".join(
                    f"{count} Φ {int(d) if float(d).is_integer() else d} mm"
                    for d, count in sorted(layer_count.items(), key=lambda item: item[0], reverse=True)
                )
                print(f"       - Camada {i + 1}               : {formatted_bars} (Área = {layer_area:.3f} cm²)")
            else:
                print(f"       - Camada {i + 1}               : (vazia)")

        print(f"       - Área total efetiva    : {self.total_as_provided:.3f} cm² (Taxa de armadura: {100 * self.total_as_provided / (self.beam.width * self.beam.height):.2f} %)")
        print(f"       - Verificação As,efetivo >= As,nec : {'OK (Atende)' if self.total_as_provided >= self.calculator.tensioned_rebar_area else 'NÃO ATENDE'}")

        if self.compressed.is_chosen and not self.calculator.is_singly_reinforced:
            print(f"\n  3.4. Detalhamento da Armadura Longitudinal de Compressão:")
            for i, layer in enumerate(self.compressed.chosen_bars):
                if layer:
                    layer_count = Counter([d.diameter_mm for d in layer])
                    formatted_bars = " + ".join(
                        f"{count} Φ {int(d) if float(d).is_integer() else d} mm"
                        for d, count in sorted(layer_count.items(), key=lambda item: item[0], reverse=True)
                    )
                    print(f"       - Camada {i + 1}               : {formatted_bars}")
            print(f"       - Área total comprimida : {self.total_as2_provided:.3f} cm²")

        # --- PASSO 4: DIMENSIONAMENTO AO CISALHAMENTO ---
        print(f"\n[PASSO 4] DIMENSIONAMENTO DA ARMADURA TRANSVERSAL (CISALHAMENTO - MODELO I)")
        print(sep_minor)
        print(f"  4.1. Verificação da Biela Comprimida de Concreto:")
        print(f"       - Força cortante solicitante Vsd : {self.design_shear_force_kN:.2f} kN")
        print(f"       - Resistência da biela VRd2      : {self.stirrup_calculator.compressed_strut_resistance:.2f} kN (alpha_v2 = {self.concrete.alpha_v2:.3f})")
        print(f"       - Verificação Vsd <= VRd2        : {'OK (Biela não esmaga)' if self.design_shear_force_kN <= self.stirrup_calculator.compressed_strut_resistance else 'FALHA (Seção insuficiente)'}")

        print(f"\n  4.2. Contribuição do Concreto e dos Estribos:")
        print(f"       - Contribuição do concreto Vc    : {self.stirrup_calculator.concrete_contribution:.2f} kN")
        print(f"       - Parcela resistida por estribos Vsw: {self.stirrup_calculator.required_contribution:.2f} kN")

        print(f"\n  4.3. Taxa de Armadura Transversal (Asw/s):")
        print(f"       - (Asw/s) calculado              : {self.stirrup_calculator.required_contribution / (0.9 * self.calculator.d * self.steel.fywd):.4f} cm²/cm ({self.stirrup_calculator.required_contribution / (0.9 * self.calculator.d * self.steel.fywd) * 100:.2f} cm²/m)")
        print(f"       - (Asw/s) mínimo (NBR 6118)      : {self.stirrup_calculator.minimum_ratio:.4f} cm²/cm ({self.stirrup_calculator.minimum_ratio * 100:.2f} cm²/m)")
        print(f"       - (Asw/s) adotado de projeto     : {self.stirrup_calculator.required_ratio:.4f} cm²/cm ({self.stirrup_calculator.required_ratio * 100:.2f} cm²/m)")
        print(f"       - Espaçamento máximo s_max       : {self.stirrup_calculator.max_spacing:.1f} cm")

        print(f"\n  4.4. Escolha e Detalhamento dos Estribos:")
        print(f"       - Diâmetro adotado (Φ)           : {self.stirrups.diameter * 10:.1f} mm")
        print(f"       - Espaçamento adotado (s)        : {self.stirrups.spacing:.1f} cm")
        print(f"       - Arranjo                        : 2 ramos Φ {self.stirrups.diameter * 10:.1f} mm c/ {self.stirrups.spacing:.1f} cm")
        print(f"       - (Asw/s) efetivo                : {self.actual_stirrup_ratio:.4f} cm²/cm ({self.actual_stirrup_ratio * 100:.2f} cm²/m)")
        print(f"       - Verificação (Asw/s) >= Nec     : {'OK (Atende)' if self.actual_stirrup_ratio >= self.stirrup_calculator.required_ratio else 'NÃO ATENDE'}")

        # --- RESUMO FINAL ---
        tension_bars_list = [d.diameter_mm for layer in self.tensioned.chosen_bars for d in layer]
        print("\n" + sep_major)
        print(" " * 28 + "RESUMO DO DETALHAMENTO")
        print(sep_major)
        print(f"  • Viga Retangular : {self.beam.width:.0f} x {self.beam.height:.0f} cm | Vão: {self.beam.length/100:.2f} m | {self.concrete.name} | {self.steel.name}")
        print(f"  • Armadura Inferior (Tração)    : " + " + ".join(
            f"{count} Φ {int(d) if float(d).is_integer() else d} mm"
            for d, count in sorted(Counter(tension_bars_list).items(), key=lambda item: item[0], reverse=True)
        ) + f"  (As = {self.total_as_provided:.2f} cm²)")
        if self.compressed.is_chosen and not self.calculator.is_singly_reinforced:
            comp_bars_list = [d.diameter_mm for layer in self.compressed.chosen_bars for d in layer]
            print(f"  • Armadura Superior (Compressão): " + " + ".join(
                f"{count} Φ {int(d) if float(d).is_integer() else d} mm"
                for d, count in sorted(Counter(comp_bars_list).items(), key=lambda item: item[0], reverse=True)
            ))
        print(f"  • Armadura Transversal (Estribos): 2 ramos Φ {self.stirrups.diameter * 10:.1f} mm c/ {self.stirrups.spacing:.1f} cm")
        print(sep_major + "\n")

