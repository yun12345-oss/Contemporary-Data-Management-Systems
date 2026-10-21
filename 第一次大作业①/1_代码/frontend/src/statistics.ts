export type CountBasis = "responses" | "people";
export function optionCount(
  option: { count: number; respondent_count: number },
  basis: CountBasis,
): number {
  return basis === "people" ? option.respondent_count : option.count;
}
export function optionPercent(
  option: { count: number; respondent_count: number },
  question: { answered: number; respondent_count: number },
  basis: CountBasis,
): number {
  const denominator =
    basis === "people" ? question.respondent_count : question.answered;
  return denominator ? (optionCount(option, basis) / denominator) * 100 : 0;
}
