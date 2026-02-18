import React, { useEffect, useState } from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import styles from "./styles/BuscaPage.module.css";

import SearchForms from "../components/Busca/SearchForms";
import ResultList from "../components/Busca/ResultList";
import SearchMaps from "../components/Busca/SearchMaps";

import {
  buscarPostos,
  fetchAnimais,
  fetchMunicipios,
} from "../services/buscaApi";

export default function BuscaPage() {
  const [form, setForm] = useState({
    endereco: "",
    numero: "",
    municipio: "",
    transporte: "",
    animal: "",
  });

  const [municipiosOptions, setMunicipiosOptions] = useState([]);
  const [animaisOptions, setAnimaisOptions] = useState([]);

  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [mun, ani] = await Promise.all([
          fetchMunicipios(),
          fetchAnimais(),
        ]);
        setMunicipiosOptions(mun);
        setAnimaisOptions(ani);
      } catch (e) {
        console.error(e);
      }
    })();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const onClear = () => {
    setForm({
      endereco: "",
      numero: "",
      municipio: "",
      transporte: "",
      animal: "",
    });
    setResultado(null);
    setErro("");
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setErro("");
    setResultado(null);

    if (!form.endereco.trim()) return setErro("Preencha o endereço.");
    if (!form.numero.trim()) return setErro("Preencha o número.");
    if (!form.municipio) return setErro("Selecione o município.");
    if (!form.transporte) return setErro("Selecione o transporte.");
    if (!form.animal) return setErro("Selecione o animal.");

    setLoading(true);
    try {
      const data = await buscarPostos({ form, limite: 10 });
      setResultado(data);
    } catch (e) {
      console.error(e);
      const msg =
        e?.response?.data?.detail ||
        e?.response?.data?.erro ||
        "Erro ao buscar. Veja o console.";
      setErro(msg);
    } finally {
      setLoading(false);
    }
  };

  const top = resultado?.top || [];

  return (
    <>
      <Header />
      <main className={styles.main}>
        <h1 className={styles.title}>Buscar Soros</h1>
        <p className={styles.subtitle}>Buscar unidade de saúde mais próxima</p>

        <SearchForms
          form={form}
          onChange={handleChange}
          onSubmit={onSubmit}
          onClear={onClear}
          loading={loading}
          erro={erro}
          municipiosOptions={municipiosOptions}
          animaisOptions={animaisOptions}
        />

        <ResultList top={top} />
        <SearchMaps resultado={resultado} top={top} />
      </main>
      <Footer />
    </>
  );
}
