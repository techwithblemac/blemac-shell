import random
import pygame

CELL = 30
HUD = 70
STEP_MS = 120

BG = (12, 6, 14)
GRID = (24, 14, 28)
SNAKE = (80, 220, 120)
HEAD = (160, 255, 190)
FOOD = (240, 70, 90)
TEXT = (235, 225, 235)
DIM = (150, 140, 155)

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)


def main(screen=None):
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()

    # Reuse the shell's window. Android allows only one.
    if screen is None:
        screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((480, 800))

    W, H = screen.get_size()
    cols = W // CELL
    rows = (H - HUD) // CELL
    ox = (W - cols * CELL) // 2
    oy = HUD + (H - HUD - rows * CELL) // 2

    font = pygame.font.Font(None, 48)
    small = pygame.font.Font(None, 32)
    clock = pygame.time.Clock()

    def new_game():
        cx, cy = cols // 2, rows // 2
        snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        return snake, RIGHT, [], place_food(snake)

    def place_food(snake):
        free = [(x, y) for x in range(cols) for y in range(rows)
                if (x, y) not in snake]
        return random.choice(free) if free else None

    snake, direction, queue, food = new_game()
    score = 0
    best = 0
    alive = True
    acc = 0
    touch_start = None
    touch_seen = False

    def turn(new):
        last = queue[-1] if queue else direction
        if new != last and (new[0] + last[0], new[1] + last[1]) != (0, 0):
            if len(queue) < 3:
                queue.append(new)

    def swipe(dx, dy):
        if abs(dx) > abs(dy):
            turn(RIGHT if dx > 0 else LEFT)
        else:
            turn(DOWN if dy > 0 else UP)

    running = True
    while running:
        dt = clock.tick(60)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:  # Android back button
                    running = False
                elif not alive and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    snake, direction, queue, food = new_game()
                    score, alive, acc = 0, True, 0
                elif e.key in (pygame.K_UP, pygame.K_w):
                    turn(UP)
                elif e.key in (pygame.K_DOWN, pygame.K_s):
                    turn(DOWN)
                elif e.key in (pygame.K_LEFT, pygame.K_a):
                    turn(LEFT)
                elif e.key in (pygame.K_RIGHT, pygame.K_d):
                    turn(RIGHT)

            # Touch (finger events use 0..1 coordinates)
            elif e.type == pygame.FINGERDOWN:
                touch_seen = True
                touch_start = (e.x * W, e.y * H)
            elif e.type == pygame.FINGERUP:
                touch_seen = True
                if touch_start:
                    dx = e.x * W - touch_start[0]
                    dy = e.y * H - touch_start[1]
                    if max(abs(dx), abs(dy)) < 30:
                        if not alive:
                            snake, direction, queue, food = new_game()
                            score, alive, acc = 0, True, 0
                    else:
                        swipe(dx, dy)
                touch_start = None

            # Mouse fallback (desktop), ignored once real touch is seen
            elif e.type == pygame.MOUSEBUTTONDOWN and not touch_seen:
                touch_start = e.pos
            elif e.type == pygame.MOUSEBUTTONUP and not touch_seen:
                if touch_start:
                    dx = e.pos[0] - touch_start[0]
                    dy = e.pos[1] - touch_start[1]
                    if max(abs(dx), abs(dy)) < 30:
                        if not alive:
                            snake, direction, queue, food = new_game()
                            score, alive, acc = 0, True, 0
                    else:
                        swipe(dx, dy)
                touch_start = None

        # Update
        if alive:
            acc += dt
            while acc >= STEP_MS:
                acc -= STEP_MS
                if queue:
                    direction = queue.pop(0)
                hx, hy = snake[0]
                nx, ny = hx + direction[0], hy + direction[1]
                if (nx < 0 or ny < 0 or nx >= cols or ny >= rows
                        or (nx, ny) in snake[:-1]):
                    alive = False
                    best = max(best, score)
                    break
                snake.insert(0, (nx, ny))
                if food and (nx, ny) == food:
                    score += 1
                    food = place_food(snake)
                else:
                    snake.pop()

        # Draw
        screen.fill(BG)
        pygame.draw.rect(screen, GRID, (ox, oy, cols * CELL, rows * CELL))

        if food:
            pygame.draw.rect(screen, FOOD,
                             (ox + food[0] * CELL + 3, oy + food[1] * CELL + 3,
                              CELL - 6, CELL - 6), border_radius=8)
        for i, (x, y) in enumerate(snake):
            pygame.draw.rect(screen, HEAD if i == 0 else SNAKE,
                             (ox + x * CELL + 1, oy + y * CELL + 1,
                              CELL - 2, CELL - 2), border_radius=6)

        screen.blit(font.render(f"Score {score}", True, TEXT), (16, 16))
        b = small.render(f"Best {best}", True, DIM)
        screen.blit(b, (W - b.get_width() - 16, 24))

        if not alive:
            msg = font.render("Game over", True, TEXT)
            sub = small.render("Tap to restart", True, DIM)
            screen.blit(msg, msg.get_rect(center=(W // 2, H // 2 - 20)))
            screen.blit(sub, sub.get_rect(center=(W // 2, H // 2 + 25)))

        pygame.display.flip()

    # Don't call pygame.quit() or display.quit(): the shell owns the window.


if __name__ == "__main__":
    main()
    pygame.quit()
