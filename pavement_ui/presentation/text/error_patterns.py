"""Engine error messages (English) and their pt-BR templates.

Each pattern matches the text of one ``raise`` in ``src``. Named groups are
inserted into the template after conversion by their name prefix:

- ``num…``: decimal point → comma (``14.0`` → ``14,0``);
- ``edge``: edge key → pt-BR edge name;
- ``rest``: translated again (the "Beam '<id>': …" prefix of design errors).
- ``ids``: engine list of quoted IDs → pt-BR quotes (``'P2', 'P3'`` → ``“P2”, “P3”``).

Order matters: the first match wins, and the prefix pattern comes last.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MessagePattern:
    """One engine message and its pt-BR template"""

    pattern: re.Pattern[str]
    template: str


def _p(regex: str, template: str) -> MessagePattern:
    return MessagePattern(re.compile(regex), template)


_ID = r"'(?P<id>[^']*)'"
_NUM = r"-?\d+(?:\.\d+)?"

PATTERNS: tuple[MessagePattern, ...] = (
    # --- inclusion rules ----------------------------------------------------
    _p(
        rf"^Pillar dimensions must be at least (?P<num_min>{_NUM}) cm\. "
        rf"Got (?P<num_w>{_NUM})×(?P<num_d>{_NUM}) cm\.$",
        "As dimensões do pilar devem ser de pelo menos {num_min} cm (NBR 6118 §13.2.3). "
        "Informado: {num_w} × {num_d} cm.",
    ),
    _p(
        rf"^Pillar gross area must be at least (?P<num_min>{_NUM}) cm²\. "
        rf"Got (?P<num_area>{_NUM}) cm²\.$",
        "A área da seção do pilar, {num_area} cm², é menor que o mínimo de "
        "{num_min} cm² (NBR 6118 §13.2.3).",
    ),
    _p(
        r"^Reference pillar ID must be included in the beam's pillar_ids\.$",
        "O pilar de referência deve estar na lista de pilares da viga.",
    ),
    _p(
        rf"^Beam {_ID} must have at least 2 pillars\.$",
        "A viga “{id}” deve ter pelo menos 2 pilares.",
    ),
    _p(
        rf"^Beam {_ID} width must be at least (?P<num_min>{_NUM}) cm\. "
        rf"Got (?P<num_w>{_NUM}) cm\.$",
        "A largura bw da viga “{id}” deve ser de pelo menos {num_min} cm "
        "(NBR 6118 §13.2.2). Informado: {num_w} cm.",
    ),
    _p(
        rf"^Beam width must be at least (?P<num_min>{_NUM}) cm\. Got (?P<num_w>{_NUM}) cm\.$",
        "A largura b deve ser de pelo menos {num_min} cm (NBR 6118 §13.2.2). "
        "Informado: {num_w} cm.",
    ),
    _p(
        rf"^Slab {_ID} must have exactly 4 corner pillars\.$",
        "A laje “{id}” deve ter exatamente 4 pilares de canto.",
    ),
    _p(
        rf"^Slab {_ID}: lowered must be >= 0 cm, got (?P<num_n>{_NUM})\.$",
        "O rebaixo da laje “{id}” deve ser ≥ 0 cm. Informado: {num_n} cm.",
    ),
    # --- validation ---------------------------------------------------------
    _p(
        r"^Concrete (?P<concrete>\S+) is below the minimum C(?P<num_min>\d+) required "
        r"for exposure class (?P<num_class>\d+)\.$",
        "O concreto {concrete} é inferior ao mínimo C{num_min} exigido para a classe "
        "de agressividade {num_class} (NBR 6118, Tabela 7.1).",
    ),
    _p(
        rf"^Beam {_ID}: pillar '(?P<pillar>[^']*)' does not exist in the registry\.$",
        "Viga “{id}”: o pilar “{pillar}” não existe.",
    ),
    _p(
        rf"^Slab {_ID}: pillar '(?P<pillar>[^']*)' does not exist in the registry\.$",
        "Laje “{id}”: o pilar “{pillar}” não existe.",
    ),
    _p(
        r"^Alignment '(?P<alignment>[^']*)' is not valid for horizontal \(X-axis\) beams\.$",
        "O alinhamento “{alignment}” não é válido para vigas horizontais (eixo X).",
    ),
    _p(
        r"^Alignment '(?P<alignment>[^']*)' is not valid for vertical \(Y-axis\) beams\.$",
        "O alinhamento “{alignment}” não é válido para vigas verticais (eixo Y).",
    ),
    _p(
        rf"^Invalid alignment for beam {_ID}\. Alignment: '(?P<alignment>[^']*)'$",
        "O alinhamento “{alignment}” não é válido para a direção da viga “{id}”.",
    ),
    _p(
        rf"^Beam {_ID}: pillar '(?P<pillar>[^']*)' cross-section .* does not fully "
        r"cover the beam width band .*$",
        "Viga “{id}”: a seção do pilar “{pillar}” não cobre toda a largura da viga.",
    ),
    _p(
        rf"^Beam {_ID} skips pillar\(s\) (?P<ids>.+?) that lie on the same\s+axis "
        r"line between its endpoints\.$",
        "A viga “{id}” pula o(s) pilar(es) {ids}, que está(ão) no mesmo eixo entre "
        "as suas extremidades.",
    ),
    _p(
        rf"^Slab {_ID}: No valid beam found for (?P<edge>\w+) edge\.$",
        "Laje “{id}”: nenhuma viga válida na borda {edge}.",
    ),
    _p(
        r"^Span between '(?P<a>[^']*)' and '(?P<b>[^']*)' already supports two slabs\.$",
        "O vão entre “{a}” e “{b}” já apoia duas lajes.",
    ),
    _p(
        r"^Supports leave no clear span: .*$",
        "Os apoios não deixam vão livre entre os pilares.",
    ),
    # --- calculation --------------------------------------------------------
    _p(
        rf"^Slab {_ID} is lowered (?P<num_x>{_NUM}) cm, but the maximum is "
        rf"(?P<num_y>{_NUM}) cm \(beam '(?P<beam>[^']*)' height (?P<num_h>{_NUM}) cm "
        rf"minus slab thickness (?P<num_t>{_NUM}) cm\)\.$",
        "A laje “{id}” está rebaixada {num_x} cm, mas o máximo é {num_y} cm (altura "
        "da viga “{beam}”, {num_h} cm, menos a espessura da laje, {num_t} cm).",
    ),
    _p(
        rf"^Slab {_ID} cannot be stabilized; required thickness exceeds (?P<num_t>{_NUM}) cm\.$",
        "A laje “{id}” não atende à flecha: a espessura necessária excede {num_t} cm "
        "(limite de 1/3 do menor vão).",
    ),
    _p(
        rf"^Deformation exceeds acceptable limits at (?P<num_x>{_NUM}) cm\..*$",
        "A flecha excede o limite L/250 em x = {num_x} cm.",
    ),
    _p(
        rf"^Required rebar area \((?P<num_a>{_NUM}) cm²\) exceeds maximum allowable "
        rf"limit \((?P<num_b>{_NUM}) cm²\)\.$",
        "A armadura necessária ({num_a} cm²) excede o máximo permitido ({num_b} cm²). "
        "Aumente a seção ou a classe do concreto.",
    ),
    _p(
        rf"^Design shear force \(V_Sd = (?P<num_a>{_NUM}) kN\) exceeds compressed strut "
        rf"resistance \(V_Rd2 = (?P<num_b>{_NUM}) kN\)\. Design not verified\.$",
        "A cortante de cálculo (VSd = {num_a} kN) excede a resistência das bielas "
        "(VRd2 = {num_b} kN). Aumente a seção ou a classe do concreto.",
    ),
    _p(
        r"^No valid reinforcement combination found\.$",
        "Nenhuma combinação de barras válida foi encontrada.",
    ),
    _p(
        r"^Effective depth \(d\) did not converge within .*$",
        "A altura útil (d) não convergiu.",
    ),
    # --- detailing ----------------------------------------------------------
    _p(
        rf"^A (?P<num_l>{_NUM}) cm φ(?P<num_d>{_NUM}) run needs a splice, "
        rf"but bars above (?P<num_max>{_NUM}) mm cannot be lap spliced\.$",
        "Uma barra Φ{num_d} de {num_l} cm precisa de emenda, mas barras acima de "
        "{num_max} mm não podem ser emendadas por traspasse (NBR 6118 §9.5.2).",
    ),
    _p(
        rf"^A (?P<num_l>{_NUM}) cm lap of φ(?P<num_d>{_NUM}) bars does not fit "
        rf"in a (?P<num_max>{_NUM}) cm bar\.$",
        "O traspasse de {num_l} cm das barras Φ{num_d} não cabe numa barra de "
        "{num_max} cm.",
    ),
    _p(
        rf"^No splice position for (?P<n>\d+)φ(?P<num_d>{_NUM}) between "
        rf"(?P<num_a>{_NUM}) and (?P<num_b>{_NUM}) cm keeps the bars spliced in one "
        r"section within Table 9\.3\.$",
        "Não há posição de emenda para {n}Φ{num_d} entre {num_a} e {num_b} cm que "
        "respeite a proporção de barras emendadas (NBR 6118, Tabela 9.3).",
    ),
    _p(
        rf"^Stirrup spacing rounds down to (?P<num_s>{_NUM}) cm, "
        rf"below the minimum of (?P<num_min>{_NUM}) cm\.$",
        "O espaçamento dos estribos arredondado, {num_s} cm, fica abaixo do mínimo "
        "de {num_min} cm.",
    ),
    _p(
        rf"^No stirrup bend diameter for CA-60 bars with (?P<num_d>{_NUM}) mm "
        r"\(φ_t > 10 mm\)\.$",
        "A NBR 6118 (Tabela 9.2) não define o dobramento de estribos CA-60 de "
        "{num_d} mm.",
    ),
    # --- NBR 6120 table lookups (KeyError) ----------------------------------
    _p(
        r"^No masonry type matching '(?P<value>[^']*)' was found\.$",
        "Alvenaria “{value}” não encontrada (NBR 6120, Tabela 2).",
    ),
    _p(
        rf"^Nominal thickness (?P<num_n>{_NUM}) cm not found for '(?P<value>[^']*)'$",
        "Espessura de {num_n} cm não disponível para essa alvenaria (NBR 6120, Tabela 2).",
    ),
    _p(
        r"^No location matching '(?P<value>[^']*)' was found\.$",
        "Uso “{value}” não encontrado na categoria da edificação (NBR 6120, Tabela 10).",
    ),
    _p(
        r"^No category matching '(?P<value>[^']*)' was found\.$",
        "Categoria “{value}” não encontrada (NBR 6120, Tabela 10).",
    ),
    # --- budget (src.data.sinapi_2026_10.steel_prices) ---------------------
    _p(
        rf"^No SINAPI price for CA(?P<grade>\d+) φ(?P<num_d>{_NUM}) mm\.$",
        "O SINAPI não tem preço para barras CA-{grade} de {num_d} mm.",
    ),
    _p(
        rf"^Concrete price must not be negative: R\$ (?P<num_p>{_NUM})/m³\.$",
        "O preço do concreto não pode ser negativo (informado: R$ {num_p}/m³).",
    ),
    # --- isolated beam files (pavement_ui.core.engine.isolated_beam_store) ---
    _p(r"^Not an isolated beam file\.$", "O arquivo não é de uma viga isolada."),
    _p(
        r"^Invalid isolated beam field '(?P<value>[^']*)'\.$",
        "Campo “{value}” ausente ou com valor inválido.",
    ),
    # --- prefix added by dimension and detail: must stay last ---------------
    _p(rf"^Beam {_ID}: (?P<rest>.+)$", "Viga “{id}”: {rest}"),
)
