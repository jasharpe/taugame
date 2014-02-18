// Reads from stdin and prints to stdout.
//
// *** INPUT ***
//
// Input format consists of space-separated integers.
//
// Integer T: number of cards on table.
// Integer D: number of cards in deck.
// T integers: cards on table.
// D integers: cards in deck. Order matters.
//
// A card is represented by an integer between 0 and 63 inclusive.
// Each pair of bits gives the value of the property.
// (This way, cards can be summed by XOR.)
//
// *** OUTPUT ***
// 
// Should be self-explanatory.
//
// *** ALGORITHM ***
// 
// Brute force try adding every selection of cards, doing a fast update of the number of bqtaus
// present. See rec routine for description of pruning.
//
// Incrementally counting the number of bqtaus is done by maintaining an array that records how many
// pairs of cards there are that have the specified sum. When a new card comes in, note for each
// bqtau it forms, there are three existing cards it could pair with to do it. Thus, bqtaus are
// triple-counted by this method.

#include <algorithm>
#include <cassert>
#include <cstdio>

using namespace std;

int const C = 64; // number of cards in full deck
int const G = 12; // goal card count

// inputs
int T, D;
int ts[G];
int ds[C];

// state
int bqtaus; // number of bqtaus present in ts[0 .. T-1]
int pair_sums[C]; // number of pairs summing to value

// update state from card i in ts array
// f = 1  => adding card
// f = -1 => removing card
__attribute__((always_inline))
void update(int i, int f)
{
  assert(f == -1 || f == 1);

  for (int j = 0; j < i; ++j) {
    int s = ts[i] ^ ts[j];
    assert(0 <= s && s < C);

    if (f == -1) --pair_sums[s];

    // This pair makes a bqtau with all pairs with equal sum.
    bqtaus += pair_sums[s] * f;

    if (f == 1) ++pair_sums[s];
  }
}

int ts_i;

void push(int card)
{
  ts[ts_i] = card;
  update(ts_i, 1);
  ++ts_i;
}

void pop()
{
  --ts_i;
  update(ts_i, -1);
}

int const inf = 123456789;
int best; // least number of bqtaus found yet in G cards
int soln[G]; // best solution found so far

// stats
int leaves; // how many times did we bottom out in the recursion?

int orderings[G+1][C]; // [depth][ ] -> indexes order of increasing marginal at specified depth
// j -- index in orderings[depth-1] array of next card to consider
void rec(int depth, int j)
{
  if (ts_i >= G) ++leaves;

  if (G == 12 && best <= 3*3) {
    // HACK: We know the best possible in 12 cards is 3. So give up.
    return;
  }

  if (bqtaus >= best) {
    // Can't possibly do better than the best we already found. Prune.
    return;
  }

  if (ts_i >= G) {
    // Reached goal. We must be a better solution, since pruning did not apply.
    assert(bqtaus < best);
    best = bqtaus;
    printf(" ... found better solution = %d\n", best / 3);
    copy(&ts[0], &ts[G], &soln[0]);
    return;
  }

  assert(j < D);

  // For each candidate card, calculate the marginal bqtau increase by adding it. Cards with smaller
  // marginal increase will be considered before cards with larger marginal increase, which promotes
  // pruning. Furthermore, the next (G - i) cards to consider give a lower bound on every possible
  // solution.
  int remain = G - ts_i;
  assert(remain > 0);

  int marginal[C]; // map from index in ds to marginal increase
  for (int k = j; k < D; ++k) {
    int old_bqtaus = bqtaus;
    push(ds[ orderings[depth-1][k] ]);
    marginal[ orderings[depth-1][k] ] = bqtaus - old_bqtaus;
    pop();

    orderings[depth][k] = orderings[depth-1][k];
  }

  sort(&orderings[depth][j], &orderings[depth][D],
    [&](int m1, int m2) -> bool {
      return marginal[m1] < marginal[m2];
  });

  int increase_lb = 0;
  for (int k = j; k < j + remain; ++k) {
    assert(k < D);
    increase_lb += marginal[ orderings[depth][k] ];
  }

  for (int k = j; k + remain <= D; ++k) {
    if (bqtaus + increase_lb >= best) {
      return;
    }

    push(ds[ orderings[depth][k] ]);
    rec(depth+1, k+1);
    pop();

    if (k + remain < D) {
      int old_lb = increase_lb;
      increase_lb -= marginal[ orderings[depth][k] ];
      increase_lb += marginal[ orderings[depth][k + remain] ];
      assert(old_lb <= increase_lb);
    }
  }
}

int main()
{
  scanf(" %d %d", &T, &D);
  assert(0 <= T && T <= G);
  assert(0 <= D && D <= C);
  assert(T + D >= G); // need to be able to reach goal

  ts_i = 0;
  bqtaus = 0;
  memset(pair_sums, 0, sizeof(pair_sums));
  for (int i = 0; i < T; ++i) {
    int t;
    scanf(" %d", &t);
    push(t);
  }
  int orig = bqtaus;
  printf("bqtaus present in original table = %d\n", orig / 3);
  for (int j = 0; j < D; ++j) {
    scanf(" %d", &ds[j]);
    orderings[0][j] = j;
  }

  leaves = 0;
  best = inf;
  rec(1, 0);
  assert(best < inf);
  assert(bqtaus == orig);

  printf("leaves explored = %d\n", leaves);
  printf("\n");
  printf("best = %d\n", best / 3);
  for (int i = 0; i < G; ++i) {
    if (i) printf(" ");
    printf("%d", soln[i]);
  }
  printf("\n");
}
