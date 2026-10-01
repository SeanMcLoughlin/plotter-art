"""
Evenly spaced streamlines for pen hatching.

Kept in its own module (not main.py) because vsketch loads sketches as
dynamic modules, which numba can't cache compiled code for.
"""

import math

import numpy as np
from numba import njit


@njit(nogil=True, cache=True)
def _streamlines(cov, ux, uy, const_dir, cx, cy, seed, res, pen_w, s_min, s_max, stop, step_mm, min_len):
    """Lines along the direction field (ux, uy) -- or the constant (cx, cy)
    when `const_dir` -- spaced so the pen's ink covers `cov` of the area.

    New lines start one spacing to the side of accepted ones (Jobard & Lefer),
    falling back to random seeds. A line ends when it comes within `stop`
    spacings of another line, leaves the active area, turns too sharply, or
    starts circling. Returns (points, offsets): line k is
    points[offsets[k]:offsets[k + 1]], in working-pixel (col, row).

    Compiled with numba and releases the GIL, so pens can run on threads.
    """
    np.random.seed(seed)
    h, w = cov.shape
    thresh = pen_w / s_max
    step = step_mm / res
    max_steps = 20000

    n_active = 0
    for r in range(h):
        for c in range(w):
            if cov[r, c] >= thresh:
                n_active += 1
    pts_out = np.empty((max(n_active // 4, 1024), 2), np.float32)
    offsets = np.zeros(1024, np.int64)
    n_lines = 0
    n_pts = 0
    if n_active == 0:
        return pts_out[:0], offsets[:1]
    act_r = np.empty(n_active, np.int32)
    act_c = np.empty(n_active, np.int32)
    k = 0
    for r in range(h):
        for c in range(w):
            if cov[r, c] >= thresh:
                act_r[k] = r
                act_c[k] = c
                k += 1
    n_random = max(1, min(n_active, int(n_active * (res / s_min) ** 2 * 3)))
    order = np.random.permutation(n_active)[:n_random]

    seed_block = np.zeros((h, w), np.uint8)
    stop_block = np.zeros((h, w), np.uint8)
    q_size = 1 << 18
    q_r = np.empty(q_size, np.float64)
    q_c = np.empty(q_size, np.float64)
    q_head = 0
    q_tail = 0
    fwd = np.empty((max_steps, 2), np.float64)
    bwd = np.empty((max_steps, 2), np.float64)
    line = np.empty((2 * max_steps + 1, 2), np.float64)
    k_next = 0

    while True:
        if q_head != q_tail:
            r0 = q_r[q_head]
            c0 = q_c[q_head]
            q_head = (q_head + 1) % q_size
        elif k_next < n_random:
            i = order[k_next]
            k_next += 1
            r0 = act_r[i] + np.random.uniform(-0.5, 0.5)
            c0 = act_c[i] + np.random.uniform(-0.5, 0.5)
        else:
            break
        if not (0 <= r0 < h and 0 <= c0 < w):
            continue
        if cov[int(r0), int(c0)] < thresh or seed_block[int(r0), int(c0)]:
            continue

        # Trace both ways from the seed.
        n_fb = np.zeros(2, np.int64)
        for side in range(2):
            buf = fwd if side == 0 else bwd
            sgn = 1.0 if side == 0 else -1.0
            r = r0
            c = c0
            pr = 0.0
            pc = 0.0
            first = True
            turned = 0.0
            n = 0
            while n < max_steps:
                ri = int(r)
                ci = int(c)
                if const_dir:
                    dx = cx
                    dy = cy
                else:
                    dx = ux[ri, ci]
                    dy = uy[ri, ci]
                if first:
                    dx *= sgn
                    dy *= sgn
                else:
                    if dx * pc + dy * pr < 0:  # orientation, not direction
                        dx = -dx
                        dy = -dy
                    if dx * pc + dy * pr < 0.5:  # too sharp a turn
                        break
                    # Stop before circling a vortex: lines don't block
                    # themselves, so a loop would ink one spot solid.
                    turned += math.asin(max(-1.0, min(1.0, pc * dy - pr * dx)))
                    if abs(turned) > 1.5 * math.pi:
                        break
                r2 = r + dy * step
                c2 = c + dx * step
                ri = int(r2)
                ci = int(c2)
                if not (0 <= r2 < h and 0 <= c2 < w):
                    break
                if cov[ri, ci] < thresh or stop_block[ri, ci]:
                    break
                buf[n, 0] = r2
                buf[n, 1] = c2
                n += 1
                r = r2
                c = c2
                pr = dy
                pc = dx
                first = False
            n_fb[side] = n

        m = n_fb[0] + n_fb[1] + 1
        if m * step_mm < min_len:
            continue
        j = 0
        for t in range(n_fb[1] - 1, -1, -1):
            line[j, 0] = bwd[t, 0]
            line[j, 1] = bwd[t, 1]
            j += 1
        line[j, 0] = r0
        line[j, 1] = c0
        j += 1
        for t in range(n_fb[0]):
            line[j, 0] = fwd[t, 0]
            line[j, 1] = fwd[t, 1]
            j += 1

        # Block the neighbourhood: seeds within one spacing, lines within
        # `stop` spacings. Points are much closer than a disc is wide, so
        # stamping about every half-radius covers the same area.
        for t in range(m):
            ri = int(line[t, 0])
            ci = int(line[t, 1])
            local = min(max(pen_w / max(cov[ri, ci], 1e-6), s_min), s_max) / res
            for blk_i in range(2):
                rad = int(round(local * (1.0 if blk_i == 0 else stop)))
                every = max(1, int(rad / (2 * step)))
                if t % every != 0 and t != m - 1:
                    continue
                blk = seed_block if blk_i == 0 else stop_block
                for dy_ in range(-rad, rad + 1):
                    rr = ri + dy_
                    if rr < 0 or rr >= h:
                        continue
                    for dx_ in range(-rad, rad + 1):
                        if dx_ * dx_ + dy_ * dy_ > rad * rad:
                            continue
                        cc = ci + dx_
                        if 0 <= cc < w:
                            blk[rr, cc] = 1
            # Seeds just over one spacing out on both sides, every few points.
            if t % 4 == 0:
                d = local * 1.05
                if const_dir:
                    nr, nc = cx, -cy
                else:
                    nr, nc = ux[ri, ci], -uy[ri, ci]
                for sg in (1.0, -1.0):
                    nxt = (q_tail + 1) % q_size
                    if nxt != q_head:
                        q_r[q_tail] = line[t, 0] + sg * nr * d
                        q_c[q_tail] = line[t, 1] + sg * nc * d
                        q_tail = nxt

        # Append to the output, growing buffers as needed.
        if n_pts + m > pts_out.shape[0]:
            grown = np.empty((max(2 * pts_out.shape[0], n_pts + m), 2), np.float32)
            grown[:n_pts] = pts_out[:n_pts]
            pts_out = grown
        if n_lines + 2 > offsets.shape[0]:
            grown_o = np.zeros(2 * offsets.shape[0], np.int64)
            grown_o[: n_lines + 1] = offsets[: n_lines + 1]
            offsets = grown_o
        for t in range(m):
            pts_out[n_pts + t, 0] = line[t, 1]  # (col, row)
            pts_out[n_pts + t, 1] = line[t, 0]
        n_pts += m
        n_lines += 1
        offsets[n_lines] = n_pts
    return pts_out[:n_pts], offsets[: n_lines + 1]


def streamlines(cov, ux, uy, seed, const_dir=None, **kw) -> list[np.ndarray]:
    """Python wrapper around the numba kernel; returns a list of polylines."""
    cx, cy = const_dir if const_dir is not None else (0.0, 0.0)
    pts, offs = _streamlines(np.ascontiguousarray(cov, np.float32), ux, uy, const_dir is not None,
                             cx, cy, seed, kw["res"], kw["pen_w"], kw["s_min"], kw["s_max"],
                             kw["stop"], kw["step_mm"], kw["min_len"])
    return [pts[offs[i]:offs[i + 1]] for i in range(len(offs) - 1)]
