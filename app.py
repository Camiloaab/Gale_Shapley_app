import gradio as gr
import random, itertools, string
import io, base64, matplotlib.pyplot as plt, networkx as nx

# ---------- Nombres ----------
MEN_NAMES   = sorted(["Abe","Ben","Cal","Dan","Eli","Fox","Gus","Hal","Mel","Tom","Zac"])
WOMEN_NAMES = sorted(["Ann","Bea","Cat","Dot","Eve","Fay","Gia","Ivy","Lea","Mia","Tea"])

# ---------- Gale–Shapley ----------
def gale_shapley(men_prefs, women_prefs, proposer="men"):
    if proposer == "women":
        swap = gale_shapley(women_prefs, men_prefs, "men")
        return {v: k for k, v in swap.items()}

    libres = list(men_prefs.keys())
    next_choice = {m: 0 for m in libres}
    engaged = {}                     # mujer -> hombre

    while libres:
        m = libres[0]
        w = men_prefs[m][next_choice[m]]
        next_choice[m] += 1
        if w not in engaged:
            engaged[w] = m
            libres.pop(0)
        else:
            m_cur = engaged[w]
            if women_prefs[w].index(m) < women_prefs[w].index(m_cur):
                engaged[w] = m
                libres[0] = m_cur
    return {m: w for w, m in engaged.items()}

# ---------- Preferencias ----------
def generate_prefs(n, mode):
    men   = MEN_NAMES[:n]
    women = WOMEN_NAMES[:n]
    men_prefs, women_prefs = {}, {}

    if mode == "Random":
        for m in men:   men_prefs[m]   = random.sample(women, n)
        for w in women: women_prefs[w] = random.sample(men,   n)

    elif mode == "Utopía":
        parejas = random.sample(women, n)
        for m, w in zip(men, parejas):
            men_prefs[m]   = [w] + random.sample([x for x in women if x != w], n-1)
            women_prefs[w] = [m] + random.sample([x for x in men   if x != m], n-1)
        for w in women:
            women_prefs.setdefault(w, random.sample(men, n))

    elif mode == "Distopía":
        orden_w = random.sample(women, n)
        orden_m = random.sample(men,   n)
        for m in men:   men_prefs[m]   = orden_w[:]
        for w in women: women_prefs[w] = orden_m[:]

    else:
        raise ValueError("Modo desconocido")

    return men, women, men_prefs, women_prefs

# ---------- Nostalgia ----------
def calc_nostalgia(match, men_prefs, women_prefs):
    men_n   = sum(men_prefs[m].index(w) + 1 for m, w in match.items())
    women_n = sum(women_prefs[w].index(m) + 1 for m, w in match.items())
    return men_n, women_n, men_n + women_n

# ---------- Estabilidad y enumeración ----------
def is_stable(match, men_prefs, women_prefs):
    inv = {w: m for m, w in match.items()}
    for m, w in match.items():
        # hombre prefiere a otra mujer y esta lo prefiere
        for w2 in men_prefs[m][:men_prefs[m].index(w)]:
            if women_prefs[w2].index(m) < women_prefs[w2].index(inv[w2]):
                return False
        # mujer prefiere a otro hombre y este la prefiere
        for m2 in women_prefs[w][:women_prefs[w].index(m)]:
            w2 = match[m2]
            if men_prefs[m2].index(w) < men_prefs[m2].index(w2):
                return False
    return True

def all_stable_matches(n, men, women, men_prefs, women_prefs):
    estables = []
    for perm in itertools.permutations(women):
        match = dict(zip(men, perm))
        if is_stable(match, men_prefs, women_prefs):
            estables.append(match)
    return estables

# ---------- HTML helpers ----------
def prefs_html(men_prefs, women_prefs):
    def tabla(titulo, prefs, quien):
        cab = "".join(f"<th>{i}</th>" for i in range(1, len(next(iter(prefs.values())))+1))
        filas = "".join(
            f"<tr><td><b>{p}</b></td>{''.join(f'<td>{x}</td>' for x in lst)}</tr>"
            for p, lst in prefs.items()
        )
        return f"<div><h4>{titulo}</h4><table border='1'><tr><th>{quien}</th>{cab}</tr>{filas}</table></div>"
    return (
    "<div style='display:flex;gap:24px;justify-content:center'>"
        f"{tabla('Preferencias de los hombres', men_prefs, 'Hombre')}"
        f"{tabla('Preferencias de las mujeres', women_prefs, 'Mujer')}"
        "</div>"
    )

def match_html(titulo, match, color):
    filas = "".join(f"<tr><td>{m}</td><td style='color:{color};font-weight:bold'>{w}</td></tr>"
                    for m, w in match.items())
    return f"<div><h4>{titulo}</h4><table border='1'><tr><th>Hombre</th><th>Mujer</th></tr>{filas}</table></div>"

def extreme_matchings_html(lab_M, M, lab_W, W):
    return (
        "<div style='display:flex;gap:40px'>"
        f"{match_html(f'Proponen mujeres ({lab_W})', W, '#e76f51')}"
        f"{match_html(f'Proponen hombres ({lab_M})', M, '#2a9d8f')}"
        "</div>"
    )

def stable_table_html(labeled):
    cab = ("<tr><th>Etiqueta</th><th>Configuración</th>"
           "<th>Nostalgia hombres</th><th>Nostalgia mujeres</th><th>Nostalgia total</th></tr>")
    filas = ""
    for lbl, match, (n_h, n_m, n_t) in labeled:
        parejas = ", ".join(f"{m}-{w}" for m, w in match.items())
        filas += f"<tr><td>{lbl}</td><td>{parejas}</td><td>{n_h}</td><td>{n_m}</td><td>{n_t}</td></tr>"
    return f"<h3>Configuraciones estables (ordenados por nostalgia femenina)</h3><table border='1'>{cab}{filas}</table>"

# ---------- Utilidad para clave canónica ----------
def match_key(match):
    return tuple(sorted(match.items()))

# ---------- Simulación (CORREGIDO) ----------
def simulate(n, mode):
    men, women, men_prefs, women_prefs = generate_prefs(n, mode)

    # Matchings extremos
    M = gale_shapley(men_prefs, women_prefs, "men")
    W = gale_shapley(men_prefs, women_prefs, "women")

    # Todas las coincidencias estables + nostalgia
    stables = all_stable_matches(n, men, women, men_prefs, women_prefs)
    datos   = [(m, calc_nostalgia(m, men_prefs, women_prefs)) for m in stables]
    datos.sort(key=lambda x: x[1][1])  # ordenar por nostalgia femenina

    # Etiquetas A, B, C...
    labeled = [(string.ascii_uppercase[i], m, r) for i, (m, r) in enumerate(datos)]

    # Diccionarios útiles
    matches   = {lbl: m for lbl, m, _ in labeled}
    etiquetas = {match_key(m): lbl for lbl, m, _ in labeled}

    # -------- construir html --------
    html_out  = prefs_html(men_prefs, women_prefs)
    html_out += "<br/>" + extreme_matchings_html(
        etiquetas.get(match_key(M), "?"), M,
        etiquetas.get(match_key(W), "?"), W
    )
    html_out += "<br/>" + stable_table_html(labeled)

    # meet, join y diagrama del reticulado
    letters, meet_tbl, join_tbl = meet_join_tables(labeled, men_prefs)
    html_out += "<br/>" + lattice_table_html("Tabla de JOIN (∨)", letters, join_tbl)
    html_out += "<br/>" + lattice_table_html("Tabla de MEET (∧)", letters, meet_tbl)

    leq = {(a, b): leq_men(matches[a], matches[b], men_prefs)
           for a in letters for b in letters}
    html_out += lattice_diagram_svg(letters, leq)

    return html_out

# ----------  Lattice helpers (NEW)  ---------------------------------

def leq_men(M1, M2, men_prefs):
    """
    Return True iff M1 <= M2 in the men-preference lattice order:
    every man likes (or ties) his partner in M1 at least as well as in M2.
    """
    for m, w1 in M1.items():
        w2 = M2[m]
        if men_prefs[m].index(w1) > men_prefs[m].index(w2):  # worse → not <=
            return False
    return True


def meet_join_tables(labeled, men_prefs):
    """
    Build two square tables (lists of lists) with the letters of meet (∧) and join (∨).
    labeled = [(letter, match_dict, nostalgia_tuple), ...] already sorted by women-nostalgia.
    """
    letters = [lbl for lbl, _, _ in labeled]
    matches = {lbl: m for lbl, m, _ in labeled}

    # convenience: pre-compute order matrix
    leq = {(a, b): leq_men(matches[a], matches[b], men_prefs) for a in letters for b in letters}

    # MEET: greatest lower bound (best for men) among those <= both
    meet = {}
    for a in letters:
        for b in letters:
            lowers = [c for c in letters if leq[(c, a)] and leq[(c, b)]]
            # pick c that is NOT <= any other lower bound strictly better for men
            best = max(lowers, key=lambda x: [men_prefs[m].index(matches[x][m]) for m in matches[x]])
            meet[(a, b)] = best

    # JOIN: least upper bound (worst for men / best for women) among those >= both
    join = {}
    for a in letters:
        for b in letters:
            uppers = [c for c in letters if leq[(a, c)] and leq[(b, c)]]
            worst = min(uppers, key=lambda x: [men_prefs[m].index(matches[x][m]) for m in matches[x]])
            join[(a, b)] = worst

    return letters, meet, join


def lattice_table_html(title, letters, table_dict):
    """Render an HTML <table> for meet or join."""
    header = "<tr><th></th>" + "".join(f"<th>{c}</th>" for c in letters) + "</tr>"
    rows = ""
    for r in letters:
        cells = "".join(f"<td>{table_dict[(r, c)]}</td>" for c in letters)
        rows += f"<tr><th>{r}</th>{cells}</tr>"
    return f"<h3>{title}</h3><table border='1'>{header}{rows}</table>"

# ---------------------------------------------------------------
#  Lattice-diagram helpers  (add after the meet/join helpers)
# ---------------------------------------------------------------

try:
    from networkx.drawing.nx_agraph import graphviz_layout
    HAS_GV = True
except Exception:
    HAS_GV = False


def hasse_edges(letters, leq):
    """Return cover relations (a,b) with a<b and no c strictly in between."""
    covers = []
    for a in letters:
        for b in letters:
            if a == b or not leq[(a, b)]:
                continue
            # is there c s.t. a<c<b ?
            if any(leq[(a, c)] and leq[(c, b)] and a != c and b != c for c in letters):
                continue
            covers.append((a, b))
    return covers


def lattice_diagram_svg(letters, leq, title="Lattice de configuraciones estables"):
    """Build a NetworkX graph of the lattice and return SVG img tag with a centered title."""
    G = nx.DiGraph()
    G.add_nodes_from(letters)
    G.add_edges_from(hasse_edges(letters, leq))

    if HAS_GV:
        pos = graphviz_layout(G, prog="dot")
    else:
        pos = nx.spring_layout(G, seed=0, k=1/len(G))

    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    nx.draw_networkx_nodes(G, pos, node_color="#90caf9", node_size=700, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight="bold", ax=ax)
    nx.draw_networkx_edges(G, pos, arrows=False, ax=ax)
    ax.axis("off")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=10)

    buf = io.BytesIO()
    plt.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    svg_data = buf.getvalue().decode()

    return f'<div style="text-align:center">{svg_data}</div>'

# ---------- Interfaz ----------
with gr.Blocks() as demo:
    gr.Image("image.png", show_label=False,show_download_button=False,show_fullscreen_button=False, height=380)
 
    with gr.Row():
        n_drop = gr.Dropdown(list(range(3, 11)), label="Número de parejas ", value=4)
        mode_drop = gr.Dropdown(
            ["Random", "Utopía", "Distopía"],
            label="Tipo de preferencias",
            value="Random",
        )
        btn = gr.Button("Play", variant="primary")
    out_html = gr.HTML()
    btn.click(simulate, inputs=[n_drop, mode_drop], outputs=out_html)

if __name__ == "__main__":
    # Advertencia: para N=10 la búsqueda exhaustiva puede tardar varios segundos.
    demo.launch()

