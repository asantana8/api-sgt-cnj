Aqui está o documento formatado em Markdown limpo, estruturado com blocos de código em PHP e tabelas para os parâmetros.

---

# WebService — Sistema de Gestão de Tabelas Processuais Unificadas (SGT/CNJ)

Já se encontra disponível o **WebService público** para o sistema de tabelas SGT no seguinte endpoint:

* **WSDL:** `[https://www.cnj.jus.br/sgt/sgt_ws.php?wsdl](https://www.cnj.jus.br/sgt/sgt_ws.php?wsdl)`

---

## Funções Disponíveis

### 1. `pesquisarItemPublicoWS`

Pesquisa as tabelas públicas de acordo com os parâmetros informados.

```php
function pesquisarItemPublicoWS($tipoTabela, $tipoPesquisa, $valorPesquisa)

```

**Parâmetros:**

| Parâmetro | Tipo | Descrição | Valores Posíveis |
| --- | --- | --- | --- |
| `$tipoTabela` | `string` | Tipo da tabela a ser pesquisada | `A` (Assuntos), `M` (Movimentos), `C` (Classes) |
| `$tipoPesquisa` | `string` | Tipo do critério de pesquisa | `G` (Glossário), `N` (Nome), `C` (Código) |
| `$valorPesquisa` | `string` | Valor do termo a ser pesquisado | Termo livre ou código |

**Retorno:** `Item[]` — Array de itens encontrados.

---

### 2. `getArrayDetalhesItemPublicoWS`

Retorna um array com os detalhes do objeto preenchido de acordo com o item requisitado.

```php
function getArrayDetalhesItemPublicoWS($seqItem, $tipoItem)

```

**Parâmetros:**

| Parâmetro | Tipo | Descrição | Valores Possíveis |
| --- | --- | --- | --- |
| `$seqItem` | `string` | Sequencial/Código do item requisitado | Código numérico do item |
| `$tipoItem` | `string` | Tipo do item | `A` (Assuntos), `M` (Movimentos), `C` (Classes) |

**Retorno:** `Array` — Array contendo as variáveis do objeto preenchidas.

---

### 3. `getArrayFilhosItemPublicoWS`

Retorna um array contendo a lista de filhos de uma determinada Classe, Assunto ou Movimento.

```php
function getArrayFilhosItemPublicoWS($seqItem, $tipoItem)

```

**Parâmetros:**

| Parâmetro | Tipo | Descrição | Valores Possíveis |
| --- | --- | --- | --- |
| `$seqItem` | `int` | Sequencial/Código do item pai | Código numérico do item |
| `$tipoItem` | `string` | Tipo do item | `A` (Assuntos), `M` (Movimentos), `C` (Classes) |

**Retorno:** `arvoreGenerica[]` — Array contendo a estrutura de nós filhos.

---

### 4. `getStringPaisItemPublicoWS`

Retorna uma string contendo o encadeamento hierárquico dos ancestrais (pais) de um item.

```php
function getStringPaisItemPublicoWS($seqItem, $tipoItem)

```

**Parâmetros:**

| Parâmetro | Tipo | Descrição | Valores Possíveis |
| --- | --- | --- | --- |
| `$seqItem` | `int` | Sequencial/Código do item requisitado | Código numérico do item |
| `$tipoItem` | `string` | Tipo do item | `A` (Assuntos), `M` (Movimentos), `C` (Classes) |

**Retorno:** `string` — Encadeamento de pais do item.

---

### 5. `getComplementoMovimentoWS`

Retorna um array contendo os complementos tabelados para os movimentos processuais.

```php
function getComplementoMovimentoWS($codMovimento)

```

**Parâmetros:**

| Parâmetro | Tipo | Descrição |
| --- | --- | --- |
| `$codMovimento` | `int` | Sequencial do movimento que se deseja obter os complementos. Se enviado vazio/nulo, traz todos os complementos cadastrados. |

**Retorno:** `ComplementoMovimento[]` — Lista de complementos vinculados.

---

### 6. `getDataUltimaVersao`

Retorna a data correspondente à última atualização da versão da tabela do SGT.

```php
function getDataUltimaVersao()

```

**Retorno:** `String` — Data da última versão publicada.