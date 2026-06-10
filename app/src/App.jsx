import { Navigate, Route, Routes } from "react-router-dom";
import ProductDetail from "./pages/ProductDetail.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/product/:id" element={<ProductDetail />} />
      <Route path="*" element={<Navigate to="/product/1" replace />} />
    </Routes>
  );
}
