
# tools.py
"""
Toda la lógica de la app:
· Algoritmo de Gale–Shapley
· Generación de preferencias y cálculo de “nostalgia”
· Enumeración de emparejamientos estables
· Construcción del reticulado, tablas ∧ / ∨ y diagrama de Hasse
· Helpers HTML con **centrado absoluto** usando flex-box
"""

import random, itertools, string, io
import matplotlib.pyplot as plt
import networkx as nx

# --------------------------------------------------
#  Nombres
# --------------------------------------------------
MEN_NAMES   = sorted(["Abe", "Ben", "Cal", "Dan", "Eli",
                      "Fox", "Gus", "Hal", "Mel", "Tom", "Zac"])
WOMEN_NAMES = sorted(["Ann", "Bea", "Cat", "Dot", "Eve",
                      "Fay", "Gia", "Ivy", "Lea", "Mia", "Tea"])

# --------------------------------------------------
#  Gale-Shapley
# --------------------------------------------------
def gale_shapley(men_prefs, women_prefs, proposer="men"):
    """Retorna un dict hombre→mujer."""
    if proposer == "women":
        swap = gale_shapley(women_prefs, men_prefs, "men")
        return {v: k for k, v in swap.items()}

    free = list(men_prefs.keys())
    next_choice = {m: 0 for m in free}
    engaged = {}                           # mujer → hombre

    while free:
        m = free[0]
        w = men_prefs[m][next_choice[m]]
        next_choice[m] += 1
        if w not in engaged:
            engaged[w] = m
            free.pop(0)
        else:
            m_cur = engaged[w]
            if women_prefs[w].index(m) < women_prefs[w].index(m_cur):
                engaged[w] = m
                free[0] = m_cur
    return {m: w for w, m in engaged.items()}

# --------------------------------------------------
#  Preferencias
# --------------------------------------------------
def generate_prefs(n, mode):
    men   = MEN_NAMES[:n]
    women = WOMEN_NAMES[:n]
    men_prefs, women_prefs = {}, {}

    if mode == "Random":
        for m in men:   men_prefs[m]   = random.sample(women, n)
        for w in women: women_prefs[w] = random.sample(men,   n)

    elif mode == "Utopía":            # cada uno tiene a su “alma gemela” arriba
        parejas = random.sample(women, n)
        for m, w in zip(men, parejas):
            men_prefs[m]   = [w] + random.sample([x for x in women if x != w], n-1)
            women_prefs[w] = [m] + random.sample([x for x in men   if x != m], n-1)
        for w in women:               # rellenar el resto
            women_prefs.setdefault(w, random.sample(men, n))

    elif mode == "Distopía":          # todos tienen la misma lista
        orden_w = random.sample(women, n)
        orden_m = random.sample(men,   n)
        for m in men:   men_prefs[m]   = orden_w[:]
        for w in women: women_prefs[w] = orden_m[:]

    else:
        raise ValueError("Modo desconocido")

    return men, women, men_prefs, women_prefs

# --------------------------------------------------
#  Métrica de “nostalgia” (regret)
# --------------------------------------------------
def calc_nostalgia(match, men_prefs, women_prefs):
    men_r   = sum(men_prefs[m].index(w)+1   for m, w in match.items())
    women_r = sum(women_prefs[w].index(m)+1 for m, w in match.items())
    return men_r, women_r, men_r + women_r

# --------------------------------------------------
#  Estabilidad y enumeración
# --------------------------------------------------
def is_stable(match, men_prefs, women_prefs):
    inv = {w: m for m, w in match.items()}
    for m, w in match.items():
        # Bloqueo: el hombre prefiere a w2 y w2 lo prefiere sobre su pareja actual
        for w2 in men_prefs[m][:men_prefs[m].index(w)]:
            if women_prefs[w2].index(m) < women_prefs[w2].index(inv[w2]):
                return False
        # Bloqueo simétrico
        for m2 in women_prefs[w][:women_prefs[w].index(m)]:
            w2 = match[m2]
            if men_prefs[m2].index(w) < men_prefs[m2].index(w2):
                return False
    return True


def all_stable_matches(n, men, women, men_prefs, women_prefs):
    stable = []
    for perm in itertools.permutations(women):
        match = dict(zip(men, perm))
        if is_stable(match, men_prefs, women_prefs):
            stable.append(match)
    return stable

# --------------------------------------------------
#  Orden del reticulado (≤ₘ) y tablas ∧ / ∨
# --------------------------------------------------
def leq_men(M1, M2, men_prefs):
    """M1 ≤ₘ M2  si todo hombre prefiere (o empata) su pareja en M1 vs M2."""
    return all(men_prefs[m].index(M1[m]) <= men_prefs[m].index(M2[m]) for m in M1)


def meet_join_tables(labeled, men_prefs):
    letters = [lbl for lbl, _, _ in labeled]
    matches = {lbl: m for lbl, m, _ in labeled}

    leq = {(a, b): leq_men(matches[a], matches[b], men_prefs)
           for a in letters for b in letters}

    meet, join = {}, {}
    for a in letters:
        for b in letters:
            lowers = [c for c in letters if leq[(c, a)] and leq[(c, b)]]
            meet[(a, b)] = max(
                lowers,
                key=lambda x: [men_prefs[m].index(matches[x][m]) for m in matches[x]]
            )
            uppers = [c for c in letters if leq[(a, c)] and leq[(b, c)]]
            join[(a, b)] = min(
                uppers,
                key=lambda x: [men_prefs[m].index(matches[x][m]) for m in matches[x]]
            )
    return letters, meet, join

# --------------------------------------------------
#  helpers de presentación 100 % CENTRADOS
# --------------------------------------------------
def _center_wrapper(html_inside: str) -> str:
    """Devuelve un contenedor flex-centrado."""
    return f"<div style='display:flex;justify-content:center'>{html_inside}</div>"


def prefs_html(men_prefs, women_prefs):
    def table(title, prefs, who):
        header = "".join(f"<th>{i}</th>" for i in range(1, len(next(iter(prefs.values())))+1))
        body   = "".join(
            f"<tr><td><b>{p}</b></td>{''.join(f'<td>{x}</td>' for x in lst)}</tr>"
            for p, lst in prefs.items()
        )
        table = (
            f"<table border='1' style='margin:0 auto;display:inline-block'>"
            f"<tr><th>{who}</th>{header}</tr>{body}</table>"
        )
        return f"<div><h4>{title}</h4>{table}</div>"

    return _center_wrapper(
        f"{table('Preferencias de los hombres', men_prefs, 'Hombre')}"
        f"{table('Preferencias de las mujeres', women_prefs, 'Mujer')}"
    )


def match_html(title, match, color, women_first=False):
    if women_first:                             #  📌  nuevo
        inv   = {w: m for m, w in match.items()}
        pairs = [(w, inv[w]) for w in sorted(inv)]          # mujer-primero
    else:
        pairs = sorted(match.items())                       # hombre-primero

    rows = "".join(
        f"<tr><td>{a}</td><td style='color:{color};font-weight:bold'>{b}</td></tr>"
        for a, b in pairs
    )
    table = (
        "<table border='1' style='display:inline-table;margin:auto'>"
        "<tr><th>Mujer</th><th>Hombre</th></tr>" if women_first
        else "<tr><th>Hombre</th><th>Mujer</th></tr>"
    ) + rows + "</table>"
    return (
        "<div><h4>{}</h4>{}</div>".format(title, table)
    )

def extreme_matchings_html(label_m, M, label_w, W):
    return (
        "<div style='display:flex;gap:40px;justify-content:center'>"
        + match_html(f'Proponen mujeres ({label_w})', W, '#e76f51', women_first=True)
        + match_html(f'Proponen hombres ({label_m})', M, '#2a9d8f', women_first=True)
        + "</div>"
    )


def stable_table_html(labeled):
    header = ("<tr><th>Etiqueta</th><th>Configuración</th>"
              "<th>Nostalgia hombres</th><th>Nostalgia mujeres</th>"
              "<th>Nostalgia total</th></tr>")
    rows = ""
    for lbl, match, (nh, nm, nt) in labeled:
        inv = {w: m for m, w in match.items()}                 # mujer-hombre
        couples = ", ".join(f"{w}-{inv[w]}" for w in sorted(inv))
        rows += f"<tr><td>{lbl}</td><td>{couples}</td><td>{nh}</td><td>{nm}</td><td>{nt}</td></tr>"

    table = (
        f"<table border='1' style='display:inline-table;margin:auto'>{header}{rows}</table>"
    )

    #            👇  ahora inline-block + texto centrado
    inner = f"<div style='display:inline-block;text-align:center'>" \
            f"<h3>Configuraciones estables (ordenados por nostalgia femenina)</h3>{table}</div>"

    return _center_wrapper(inner)


def lattice_table_html(title, letters, table_dict):
    header = "<tr><th></th>" + "".join(f"<th>{c}</th>" for c in letters) + "</tr>"
    rows = ""
    for r in letters:
        rows += "<tr><th>{}</th>{}</tr>".format(
            r, "".join(f"<td>{table_dict[(r,c)]}</td>" for c in letters)
        )

    table = (
        f"<table border='1' style='margin:0 auto;display:inline-block'>{header}{rows}</table>"
    )
    return _center_wrapper(f"<div><h3>{title}</h3>{table}</div>")

# --------------------------------------------------
#  Diagrama de Hasse
# --------------------------------------------------
def hasse_edges(letters, leq):
    covers = []
    for a in letters:
        for b in letters:
            if a == b or not leq[(a, b)]:
                continue
            if any(leq[(a, c)] and leq[(c, b)] for c in letters if c not in (a, b)):
                continue
            covers.append((a, b))
    return covers


try:
    from networkx.drawing.nx_agraph import graphviz_layout
    _HAS_GV = True
except Exception:  # sin graphviz
    _HAS_GV = False


def lattice_diagram_svg(letters, leq, title="Lattice de configuraciones estables"):
    G = nx.DiGraph()
    G.add_nodes_from(letters)
    G.add_edges_from(hasse_edges(letters, leq))

    pos = graphviz_layout(G, prog="dot") if _HAS_GV else nx.spring_layout(G, seed=0, k=1/len(G))

    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    nx.draw_networkx_nodes(G, pos, node_color="#90caf9", node_size=700, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight="bold", ax=ax)
    nx.draw_networkx_edges(G, pos, arrows=False, ax=ax)
    ax.axis("off")
    ax.set_title(title, fontweight="bold", fontsize=14, pad=10)

    buf = io.BytesIO()
    plt.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)

    return _center_wrapper(buf.getvalue().decode())

# --------------------------------------------------
#  Punto de entrada para Gradio
# --------------------------------------------------
def simulate(n, mode):
    men, women, men_prefs, women_prefs = generate_prefs(n, mode)

    # matchings extremos
    M = gale_shapley(men_prefs, women_prefs, "men")
    W = gale_shapley(men_prefs, women_prefs, "women")

    # todas las coincidencias estables
    stables = all_stable_matches(n, men, women, men_prefs, women_prefs)
    datos   = [(m, calc_nostalgia(m, men_prefs, women_prefs)) for m in stables]
    datos.sort(key=lambda x: x[1][1])                   # por nostalgia femenina

    # etiquetar A, B, C…
    labeled = [(string.ascii_uppercase[i], m, r) for i, (m, r) in enumerate(datos)]
    matches = {lbl: m for lbl, m, _ in labeled}
    labels  = {tuple(sorted(m.items())): lbl for lbl, m, _ in labeled}

    # construir HTML en partes centradas
    parts = [
        prefs_html(men_prefs, women_prefs),
        extreme_matchings_html(labels.get(tuple(sorted(M.items())), "?"), M,
                               labels.get(tuple(sorted(W.items())), "?"), W),
        stable_table_html(labeled)
    ]

    letters, meet_tbl, join_tbl = meet_join_tables(labeled, men_prefs)
    parts.append(lattice_table_html("Tabla de JOIN (∨)", letters, join_tbl))
    parts.append(lattice_table_html("Tabla de MEET (∧)", letters, meet_tbl))

    leq = {(a, b): leq_men(matches[a], matches[b], men_prefs)
           for a in letters for b in letters}
    parts.append(lattice_diagram_svg(letters, leq))

    # juntar todo (no hace falta wrapper extra: cada bloque ya está centrado)
    return "<br/>".join(parts)
