import axios from "axios";

export const API_URL = "http://localhost:8000";

export function transporteParaModo(transporte) {
  const t = (transporte || "").toLowerCase();
  if (t.includes("pé") || t.includes("pe")) return "caminhando";
  if (t.includes("ambul")) return "carro";
  return "carro";
}

export function montarEnderecoCompleto({ endereco, numero, municipio }) {
  const rua = (endereco || "").trim();
  const num = (numero || "").trim();
  const mun = (municipio || "").trim();

  let full = rua;
  if (num) full += `, ${num}`;
  if (mun) full += ` - ${mun} - SP, Brasil`;
  else full += ` - SP, Brasil`;

  return full;
}

export async function fetchMunicipios() {
  const res = await axios.get(`${API_URL}/dashboard/municipios`);
  return (res.data || []).map((m) => ({ label: m.nome, value: m.nome }));
}

// Mantém fixo como você quer (Serpente/Aranha/Escorpião)
export async function fetchAnimais() {
  return [
    { label: "Serpente", value: "Serpente" },
    { label: "Aranha", value: "Aranha" },
    { label: "Escorpião", value: "Escorpião" },
  ];
}

export async function buscarPostos({ form, limite = 10 }) {
  const endereco = montarEnderecoCompleto(form);
  const modo = transporteParaModo(form.transporte);

  const res = await axios.get(`${API_URL}/busca/postos`, {
    params: {
      endereco,
      animal: form.animal,
      modo,
      limite,
    },
  });

  return res.data;
}
