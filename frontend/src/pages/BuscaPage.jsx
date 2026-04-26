import React, { useEffect, useState } from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import styles from "./styles/BuscaPage.module.css";
import { useLocation } from "react-router-dom";
import SearchForms from "../components/Busca/SearchForms";
import ResultList from "../components/Busca/ResultList";
import SearchMaps from "../components/Busca/SearchMaps";
import { buscarPostos, fetchAnimais, fetchMunicipios, reverseGeocode } from "../services/buscaApi";

function normalizeText(value) {
  if (!value) return "";
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export default function BuscaPage() {
  const location = useLocation();

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
  const [loadingGeo, setLoadingGeo] = useState(false);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState(null);
  const [geoCoords, setGeoCoords] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [mun, ani] = await Promise.all([fetchMunicipios(), fetchAnimais()]);
        setMunicipiosOptions(mun);
        setAnimaisOptions(ani);
      } catch (e) { console.error(e); }
    })();
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const q = (params.get("q") || "").trim();
    if (!q) return;

    const digitsOnly = q.replace(/\D/g, "");
    if (digitsOnly.length === 8) {
      setForm((prev) => ({
        ...prev,
        cep: digitsOnly,
      }));
      return;
    }

    const normalizedQuery = normalizeText(q);
    const matchedMunicipio = municipiosOptions.find((opt) => {
      const optionValue = normalizeText(opt?.value || opt?.label);
      return optionValue === normalizedQuery || optionValue.includes(normalizedQuery);
    });

    setForm((prev) => ({
      ...prev,
      municipio: matchedMunicipio?.value || q,
    }));
  }, [location.search, municipiosOptions]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const onClear = () => {
    setForm({ endereco: "", numero: "", bairro: "", cep: "", municipio: "", transporte: "", animal: "" });
    setResultado(null);
    setErro("");
    setGeoCoords(null);
  };

  const onUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      setErro("Seu navegador não suporta geolocalização.");
      return;
    }

    setErro("");
    setLoadingGeo(true);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        setGeoCoords({ latitude, longitude });

        try {
          const enderecoAtual = await reverseGeocode(latitude, longitude);
          const municipioNormalizado = normalizeText(enderecoAtual?.municipio);
          const municipioEncontrado = municipioNormalizado
            ? municipiosOptions.find((opt) => {
              const valor = normalizeText(opt?.value || opt?.label);
              return valor === municipioNormalizado || valor.includes(municipioNormalizado);
            })
            : null;

          setForm((prev) => ({
            ...prev,
            endereco: enderecoAtual?.endereco || prev.endereco,
            numero: enderecoAtual?.numero || prev.numero,
            bairro: enderecoAtual?.bairro || prev.bairro,
            municipio: municipioEncontrado?.value || prev.municipio,
            cep: enderecoAtual?.cep || prev.cep,
          }));

          if (!municipioEncontrado && enderecoAtual?.municipio) {
            setErro("Localização obtida, mas não foi possível casar o município automaticamente. Selecione manualmente.");
          }
        } catch (reverseError) {
          console.error(reverseError);
          setErro("Localização capturada, mas não foi possível preencher o endereço automaticamente.");
        } finally {
          setLoadingGeo(false);
        }
      },
      (geoError) => {
        setLoadingGeo(false);

        if (geoError.code === geoError.PERMISSION_DENIED) {
          setErro("Permissão de localização negada. Você pode preencher o endereço manualmente.");
          return;
        }

        if (geoError.code === geoError.TIMEOUT) {
          setErro("Não foi possível obter sua localização a tempo. Tente novamente.");
          return;
        }

        setErro("Não foi possível obter sua localização atual.");
      },
      {
        enableHighAccuracy: true,
        timeout: 20000,
        maximumAge: 0,
      },
    );
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setErro("");
    setResultado(null);

    // Validação flexível
    const cepNumerico = form.cep.replace(/\D/g, "");
    const hasCep = cepNumerico.length === 8;
    const hasAddress = form.endereco.trim().length > 2;
    const hasMunicipio = form.municipio.trim().length > 0;
    const hasGeo = Boolean(geoCoords?.latitude && geoCoords?.longitude);

    if (!hasCep && !hasAddress && !hasMunicipio && !hasGeo) {
      return setErro("Preencha CEP, endereço, município ou use sua localização atual.");
    }
    if (!hasGeo && !hasCep && !hasMunicipio) {
      return setErro("Selecione o município, informe um CEP ou use sua localização atual.");
    }
    if (!form.animal) return setErro("Selecione o animal.");

    setLoading(true);
    try {
      // Enviamos o CEP já normalizado para a API
      const data = await buscarPostos({
        ...form,
        cep: cepNumerico,
        limite: 10,
        latitude: geoCoords?.latitude,
        longitude: geoCoords?.longitude,
      });
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
          onUseCurrentLocation={onUseCurrentLocation}
          loading={loading}
          loadingGeo={loadingGeo}
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