TIPOS_CLIENTE_LOCACAO = (
    ("PROPRIETARIO", "Proprietário"),
    ("INQUILINO", "Inquilino"),
    ("FIADOR", "Fiador")
)

SEXO_MAP = {"1": "M", "2": "F", "3": "I"}

mapa_tipos_imovel = {
    '1': 'Casa',
    '2': 'Garagem',
    '3': 'Apartamento',
    '4': 'Chácara',
    '5': 'Apartamento duplex',
    '6': 'Sala comercial',
    '7': 'Sítio',
    '8': 'Cobertura',
    '9': 'Rancho',
    '10': 'Casa comercial',
    '11': 'Apartamento tipo kitnet',
    '12': 'Área comum',
    '13': 'Sobrado',
    '14': 'Fazenda',
    '15': 'Barracão',
    '16': 'Loja',
    '17': 'Edícula',
    '18': 'Prédio',
    '19': 'Casa assobradada',
    '20': 'Conjunto',
    '21': 'Outro',
    '22': 'Casa em condomínio',
    '23': 'Escritório',
    '24': 'Galpão',
    '25': 'Flat',
    '26': 'Andar corporativo',
    '27': 'Bangalô',
    '28': 'Haras',
    '29': 'Box/Garagem',
    '30': 'Área'
}

mapa_tipos_contrato = {
    '1': 'Residencial',
    '2': 'Não residencial',
    '3': 'Comercial',
    '4': 'Indústria',
    '5': 'Temporada',
    '7': 'Misto'
}

mapa_categoricos = {
    '0': 'Não',
    '1': 'Sim',
    '2': 'Sim',
    '4': 'Suspenso'
}

mapa_garantias = {
    '0': "Sem garantia",
    '1': "Fiador",
    '2': "Caução",
    '3': "Seguro fiança",
    '4': "Título de capitalização",
    '5': "Caucionante",
    '6': "Cessão fiduciária",
    '7': "Caução PJBank"
}

mapa_aluguel_garantido = {
    '': "Não garantido",
    '1': "Garantir todo boleto",
    '2': "Garantir apenas aluguel",
    '3': "Garantir produtos marcados",
    '4': "Garantir apenas aluguel e IR"
}