volatile unsigned counter = 0;
void spin(void) { counter += 1; }
int main(void) {
  for (int i = 0; i < 4; i++) { spin(); }
  return 0;
}
