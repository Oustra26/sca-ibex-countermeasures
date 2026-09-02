// ==========================================================
// SCA DEBUG SIGNALS - instrumentation pour traces Verilator
// Ces signaux servent uniquement a l'observation dans les VCD/FST
// ==========================================================
/* verilator lint_off UNUSEDSIGNAL */

logic [31:0] sca_dbg_instr;
logic [31:0] sca_dbg_instr_alu;
logic [31:0] sca_dbg_pc;
logic [31:0] sca_dbg_rf_rdata_a;
logic [31:0] sca_dbg_rf_rdata_b;
logic [31:0] sca_dbg_alu_op_a;
logic [31:0] sca_dbg_alu_op_b;
logic [31:0] sca_dbg_result_ex;
logic [31:0] sca_dbg_rf_wdata_wb;
logic [7:0]  sca_dbg_alu_operator;
logic        sca_dbg_trigger;

logic        sca_dbg_trigger_ex;

/*|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
  Instrumentation : equilibrage logique (dual-rail)
  Un seul bloc d'instrumentation doit rester actif a la fois :
  les blocs masquage / dual-rail / hybride partagent des adresses
  et doivent etre mis en commentaire tour a tour.
|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||*/
logic trigger_match_dual_true;
logic trigger_match_dual_false;

logic sca_dbg_trigger_dual_true_ex;
logic sca_dbg_trigger_dual_false_ex;

logic sca_dbg_trigger_dual_true;
logic sca_dbg_trigger_dual_false;

// Detection du debut de sequence (dual-rail)
assign trigger_match_dual_true =
    instr_valid_id &&
    (pc_id == 32'h00100348);

assign trigger_match_dual_false =
    instr_valid_id &&
    (pc_id == 32'h00100350);

// Cote pipeline (dual-rail)
always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
        sca_dbg_trigger_dual_true_ex  <= 1'b0;
        sca_dbg_trigger_dual_false_ex <= 1'b0;
    end else begin
        sca_dbg_trigger_dual_true_ex  <= trigger_match_dual_true;
        sca_dbg_trigger_dual_false_ex <= trigger_match_dual_false;
    end
end

assign sca_dbg_trigger_dual_true  = sca_dbg_trigger_dual_true_ex;
assign sca_dbg_trigger_dual_false = sca_dbg_trigger_dual_false_ex;

/*|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
  Instrumentation : version de base non protegee
|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||*/
assign trigger_match =
    instr_valid_id &&
    (instr_rdata_alu_id == 32'h01184633) &&   // xor a2, a6, a7
    (pc_id             == 32'h001003FE);

always_ff @(posedge clk_i or negedge rst_ni) begin
  if (!rst_ni)
    sca_dbg_trigger_ex <= 1'b0;
  else
    sca_dbg_trigger_ex <= trigger_match;
end

assign sca_dbg_trigger = sca_dbg_trigger_ex;

// --- Signaux de donnees communs a toutes les versions ---------
assign sca_dbg_instr        = instr_rdata_id;
assign sca_dbg_instr_alu    = instr_rdata_alu_id;
assign sca_dbg_pc           = pc_id;
assign sca_dbg_rf_rdata_a   = rf_rdata_a;
assign sca_dbg_rf_rdata_b   = rf_rdata_b;
assign sca_dbg_alu_op_a     = alu_operand_a_ex;
assign sca_dbg_alu_op_b     = alu_operand_b_ex;
assign sca_dbg_result_ex    = result_ex;
assign sca_dbg_rf_wdata_wb  = rf_wdata_wb;
assign sca_dbg_alu_operator = 8'(alu_operator_ex);

/*|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
  Instrumentation : masquage booleen
|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||*/
logic sca_dbg_trigger_mask_a;
logic sca_dbg_trigger_mask_b;
logic sca_dbg_trigger_recombine;

logic trigger_match_mask_a;
logic trigger_match_mask_b;
logic trigger_match_recombine;

logic sca_dbg_trigger_mask_a_ex;
logic sca_dbg_trigger_mask_b_ex;
logic sca_dbg_trigger_recombine_ex;

// Detections pour le masquage (opcode xor a5, a0, a1)
assign trigger_match_mask_a =
    instr_valid_id &&
    (instr_rdata_alu_id == 32'h00B547B3) &&
    (pc_id             == 32'h00100348);

assign trigger_match_mask_b =
    instr_valid_id &&
    (instr_rdata_alu_id == 32'h00B547B3) &&
    (pc_id             == 32'h00100350);

assign trigger_match_recombine =
    instr_valid_id &&
    (instr_rdata_alu_id == 32'h00B547B3) &&
    (pc_id             == 32'h0010035A);

// Versions retardees d'un cycle (alignement sur l'etage EX)
always_ff @(posedge clk_i or negedge rst_ni) begin
  if (!rst_ni) begin
    sca_dbg_trigger_mask_a_ex    <= 1'b0;
    sca_dbg_trigger_mask_b_ex    <= 1'b0;
    sca_dbg_trigger_recombine_ex <= 1'b0;
  end else begin
    sca_dbg_trigger_mask_a_ex    <= trigger_match_mask_a;
    sca_dbg_trigger_mask_b_ex    <= trigger_match_mask_b;
    sca_dbg_trigger_recombine_ex <= trigger_match_recombine;
  end
end

assign sca_dbg_trigger_mask_a    = sca_dbg_trigger_mask_a_ex;
assign sca_dbg_trigger_mask_b    = sca_dbg_trigger_mask_b_ex;
assign sca_dbg_trigger_recombine = sca_dbg_trigger_recombine_ex;

/*|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
  Instrumentation : randomisation temporelle
|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||*/
logic sca_dbg_trigger_random;
logic trigger_match_random;
logic sca_dbg_trigger_random_ex;

// Detection du debut de sequence (randomisation temporelle)
assign trigger_match_random =
    instr_valid_id &&
    (pc_id == 32'h00100348);

// Alignement sur l'etage EX (randomisation temporelle)
always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni)
        sca_dbg_trigger_random_ex <= 1'b0;
    else
        sca_dbg_trigger_random_ex <= trigger_match_random;
end

// Export du signal (randomisation temporelle)
assign sca_dbg_trigger_random = sca_dbg_trigger_random_ex;

/*|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
  Instrumentation : version hybride
  (masquage booleen + randomisation temporelle)

  Quatre triggers separes, alignes sur les fonctions du binaire
  hello_test.elf compile pour la version hybride :

    sca_dbg_trigger_rand           -> entree de random_delay
    sca_dbg_trigger_hyb_mask_a     -> XOR de mask_share_a
    sca_dbg_trigger_hyb_mask_b     -> XOR de mask_share_b
    sca_dbg_trigger_hyb_recombine  -> XOR de recombine_shares

  Adresses extraites par objdump sur le binaire de la campagne.
|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||*/

// --- Adresses cibles ------------------------------------------
localparam logic [31:0] PC_RAND_DELAY    = 32'h00100348;
localparam logic [31:0] PC_HYB_MASK_A    = 32'h00100360;
localparam logic [31:0] PC_HYB_MASK_B    = 32'h00100368;
localparam logic [31:0] PC_HYB_RECOMBINE = 32'h00100372;

// Opcode XOR commun aux trois fonctions de masquage
// (xor a5, a0, a1 == 0x00B547B3 en RV32I non compresse)
localparam logic [31:0] OPCODE_XOR_HYB   = 32'h00B547B3;

// --- Declarations des signaux de trigger ----------------------
logic trigger_match_rand;
logic trigger_match_hyb_mask_a;
logic trigger_match_hyb_mask_b;
logic trigger_match_hyb_recombine;

logic sca_dbg_trigger_rand_ex;
logic sca_dbg_trigger_hyb_mask_a_ex;
logic sca_dbg_trigger_hyb_mask_b_ex;
logic sca_dbg_trigger_hyb_recombine_ex;

logic sca_dbg_trigger_rand;
logic sca_dbg_trigger_hyb_mask_a;
logic sca_dbg_trigger_hyb_mask_b;
logic sca_dbg_trigger_hyb_recombine;

// --- Conditions de declenchement ------------------------------
// Randomisation : entree de random_delay (instruction addi sp, sp, -16).
// Pas de condition d'opcode : on prend le premier cycle de la fonction.
assign trigger_match_rand =
    instr_valid_id &&
    (pc_id == PC_RAND_DELAY);

// Masquage : XOR exact a l'adresse de chaque fonction.
// Les trois fonctions debutent directement par l'instruction XOR cible.
assign trigger_match_hyb_mask_a =
    instr_valid_id &&
    (instr_rdata_alu_id == OPCODE_XOR_HYB) &&
    (pc_id             == PC_HYB_MASK_A);

assign trigger_match_hyb_mask_b =
    instr_valid_id &&
    (instr_rdata_alu_id == OPCODE_XOR_HYB) &&
    (pc_id             == PC_HYB_MASK_B);

assign trigger_match_hyb_recombine =
    instr_valid_id &&
    (instr_rdata_alu_id == OPCODE_XOR_HYB) &&
    (pc_id             == PC_HYB_RECOMBINE);

// --- Retard d'un cycle pour aligner sur l'etage EX ------------
always_ff @(posedge clk_i or negedge rst_ni) begin
  if (!rst_ni) begin
    sca_dbg_trigger_rand_ex          <= 1'b0;
    sca_dbg_trigger_hyb_mask_a_ex    <= 1'b0;
    sca_dbg_trigger_hyb_mask_b_ex    <= 1'b0;
    sca_dbg_trigger_hyb_recombine_ex <= 1'b0;
  end else begin
    sca_dbg_trigger_rand_ex          <= trigger_match_rand;
    sca_dbg_trigger_hyb_mask_a_ex    <= trigger_match_hyb_mask_a;
    sca_dbg_trigger_hyb_mask_b_ex    <= trigger_match_hyb_mask_b;
    sca_dbg_trigger_hyb_recombine_ex <= trigger_match_hyb_recombine;
  end
end

// --- Export des signaux pour GTKWave --------------------------
assign sca_dbg_trigger_rand          = sca_dbg_trigger_rand_ex;
assign sca_dbg_trigger_hyb_mask_a    = sca_dbg_trigger_hyb_mask_a_ex;
assign sca_dbg_trigger_hyb_mask_b    = sca_dbg_trigger_hyb_mask_b_ex;
assign sca_dbg_trigger_hyb_recombine = sca_dbg_trigger_hyb_recombine_ex;

// --- Fin instrumentation --------------------------------------
