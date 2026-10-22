import React from 'react';

// Formatea los dígitos desplazando hacia la izquierda: MM:SS, o HH:MM:SS a partir de 5 dígitos
const formatDigits = (digits) => {
    const padded = digits.padStart(digits.length > 4 ? 6 : 4, '0');
    return padded.match(/../g).join(':');
};

export default function TimeInput({ label, value = '00:00', onChange }) {
    // Se trabaja sobre los dígitos del texto resultante, así funcionan igual teclear, borrar y pegar
    const handleChange = (e) => {
        const digits = e.target.value.replace(/\D/g, '').replace(/^0+/, '').slice(-6);
        onChange(formatDigits(digits));
    };

    return (
        <div>
            <label className="block text-xs font-medium text-zinc-300 mb-2">
                {label}
            </label>
            <input
                type="text"
                inputMode="numeric"
                value={value}
                onChange={handleChange}
                placeholder="00:00"
                className="w-full bg-[#0b0c0e] border border-[#262a33] rounded-md px-3.5 py-2 text-sm text-center font-mono text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-400 transition-colors select-none"
            />
        </div>
    );
}
