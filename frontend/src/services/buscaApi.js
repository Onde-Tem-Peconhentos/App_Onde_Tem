import axios from "axios";

export const API_URL = "http://localhost:8000";

export async function fetchMunicipios() {
  const res = await axios.get(`${API_URL}/dashboard/municipios`);
  return (res.data || []).map((m) => ({ label: m.nome, value: m.nome }));
}

export async function fetchAnimais() {
  return [
    { label: "Serpente: Jararaca (Botrópico)", value: "Jararaca" },
    { label: "Serpente: Cascavel (Crotálico)", value: "Cascavel" },
    { label: "Serpente: Coral (Elapídico)", value: "Coral" },
    { label: "Escorpião", value: "Escorpião" },
    { label: "Aranha", value: "Aranha" },
    { label: "Lagarta: Taturana (Lonomia)", value: "Lagarta" },
  ];
}

export async function buscarPostos(form) {
  const res = await axios.get(`${API_URL}/busca/postos`, {
    params: {
      endereco: form.endereco,
      numero: form.numero,
      bairro: form.bairro,
      cep: form.cep, // Aqui o CEP já vai limpo
      municipio: form.municipio,
      latitude: form.latitude,
      longitude: form.longitude,
      animal: form.animal,
      modo: (form.transporte || "").toLowerCase(),
      limite: form.limite || 10,
    },
  });
  return res.data;
}

export async function reverseGeocode(latitude, longitude) {
  const res = await axios.get(`${API_URL}/busca/reverse-geocode`, {
    params: {
      latitude,
      longitude,
    },
  });
  return res.data;
}