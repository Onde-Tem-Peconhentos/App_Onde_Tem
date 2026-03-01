import React, { useEffect, useState } from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import styles from "./styles/BuscaPage.module.css";
import SearchForms from "../components/Busca/SearchForms";
import ResultList from "../components/Busca/ResultList";
import SearchMaps from "../components/Busca/SearchMaps";
import { buscarPostos, fetchAnimais, fetchMunicipios } from "../services/buscaApi";

export default function BuscaPage() {
  const [form, setForm] = useState({
    endereco: "",
    numero: "",
    bairro: "",
    cep: "",
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
        const [mun, ani] = await Promise.all([fetchMunicipios(), fetchAnimais()]);
        setMunicipiosOptions(mun);
        setAnimaisOptions(ani);
      } catch (e) { console.error(e); }
    })();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const onClear = () => {
    setForm({ endereco: "", numero: "", bairro: "", cep: "", municipio: "", transporte: "", animal: "" });
    setResultado(null);
    setErro("");
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setErro("");
    setResultado(null);

    // Validação flexível
    const cepNumerico = form.cep.replace(/\D/g, "");
    const hasCep = cepNumerico.length === 8;
    const hasAddress = form.endereco.trim().length > 2;

    if (!hasCep && !hasAddress) {
      return setErro("Preencha o CEP ou o endereço corretamente.");
    }
    if (!form.municipio) return setErro("Selecione o município.");
    if (!form.animal) return setErro("Selecione o animal.");

    setLoading(true);
    try {
      // Enviamos o CEP já normalizado para a API
      const data = await buscarPostos({ ...form, cep: cepNumerico, limite: 10 });
      if (data.erro) setErro(data.erro);
      else setResultado(data);
    } catch (e) {
      setErro(e?.response?.data?.detail || "Erro na busca.");
    } finally { setLoading(false); }
  };

  return (
    <>
      <Header />
      <main className={styles.main}>
        <h1 className={styles.title}>Buscar Soros</h1>
        <p className={styles.subtitle}>Encontre a unidade de saúde mais próxima</p>
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
        {resultado && <ResultList top={resultado.top} />}
        {resultado && <SearchMaps resultado={resultado} top={resultado.top} />}
      </main>
      <Footer />
    </>
  );
}