# Métricas analíticas

Os endpoints analíticos recebem `company_id`, `start_date` e `end_date`.

- Receita e despesa realizadas consideram transações pagas.
- Resultado é receita menos despesa.
- Margem é `resultado / receita × 100`; sem receita, retorna `null`.
- Inadimplência compara o valor vencido com o total de contas a receber.
- Fluxo de caixa organiza entradas e saídas no período.

Sempre interprete previsões e anomalias como apoio exploratório sobre dados sintéticos, não como recomendação financeira.
