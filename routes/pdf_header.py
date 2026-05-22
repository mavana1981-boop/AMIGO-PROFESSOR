"""
Cabeçalho padronizado para todos os relatórios PDF do Amigo do Professor.
Inclui: logo do DF (esquerda), nome da escola e professora (centro/direita).
"""
import os, io

_LOGO_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'logo_df.png')


def cabecalho_pdf(story, prof_nome: str, escola: str, titulo_relatorio: str = ""):
    """
    Adiciona cabeçalho padrão ao story do ReportLab.
    Deve ser chamado logo após criar o story = [].
    """
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    from reportlab.platypus import Image as RLImage

    NAVY  = colors.HexColor("#1a3a5c")
    CINZA = colors.HexColor("#6b7280")
    SS    = getSampleStyleSheet()

    T_escola = ParagraphStyle("esc", parent=SS["Normal"],
                               fontSize=9, fontName="Helvetica-Bold",
                               textColor=NAVY, leading=13)
    T_prof   = ParagraphStyle("prof", parent=SS["Normal"],
                               fontSize=8, textColor=CINZA, leading=11)
    T_titulo = ParagraphStyle("tit", parent=SS["Normal"],
                               fontSize=8, textColor=CINZA, leading=11,
                               alignment=TA_RIGHT)

    # Logo
    try:
        logo = RLImage(_LOGO_PATH, width=1.4*cm, height=1.7*cm)
    except Exception:
        logo = Paragraph("", SS["Normal"])

    # Coluna do meio: escola + professora
    meio = [
        Paragraph(escola or "Escola não informada", T_escola),
        Paragraph(f"Prof(a): {prof_nome or 'Não informado'}", T_prof),
    ]

    # Coluna direita: título do relatório
    direita = [
        Paragraph(titulo_relatorio, T_titulo),
        Paragraph("Secretaria de Estado de Educação do DF", T_titulo),
    ]

    cab_data = [[logo, meio, direita]]
    cab = Table(cab_data, colWidths=[1.8*cm, None, 6*cm])
    cab.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))

    story.append(cab)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY))
    story.append(Spacer(1, 8))
