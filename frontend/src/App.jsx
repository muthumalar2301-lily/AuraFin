import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  Container,
  Row,
  Col,
  Card,
  Form,
  Button,
  Alert,
  Badge,
  Spinner,
} from "react-bootstrap";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

import { Line } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  "https://aurafin-backend-3kwv.onrender.com"
).replace(/\/+$/, "") + "/api";

export default function App() {
  // Summary & Cash Flow State
  const [summary, setSummary] = useState(null);
  const [delayScenario, setDelayScenario] = useState(false);

  // Pricing Advisor State
  const [pricingInputs, setPricingInputs] = useState({
    materials: 12,
    hours: 2,
    rate: 20,
    packaging: 3,
    shipping: 7,
    overhead: 2,
    target_margin: 30,
  });

  const [pricingResult, setPricingResult] = useState(null);

  // PayPal Invoicing State
  const [invoiceEmail, setInvoiceEmail] = useState(
    "buyer-sandbox@business.example.com"
  );
  const [invoiceItem, setInvoiceItem] = useState(
    "Custom Art Print Batch"
  );
  const [invoiceStatus, setInvoiceStatus] = useState(null);
  const [sendingInvoice, setSendingInvoice] = useState(false);

  // Gemini AI Assistant State
  const [chatPrompt, setChatPrompt] = useState(
    "Can I afford to purchase a $60 software tool today?"
  );
  const [chatReply, setChatReply] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  // Load Dashboard Summary
  const fetchSummary = async () => {
    try {
      const res = await axios.get(`${API_BASE}/dashboard/summary`);
      setSummary(res.data);
    } catch (err) {
      console.error("Failed to load dashboard summary:", err);
    }
  };

  useEffect(() => {
    fetchSummary();
    handleCalculatePrice();
  }, []);

  // Pricing Engine Handler
  const handleCalculatePrice = async () => {
    try {
      const res = await axios.post(
        `${API_BASE}/pricing/calculate`,
        pricingInputs
      );

      setPricingResult(res.data);
    } catch (err) {
      console.error("Error calculating price:", err);
    }
  };

  // PayPal Invoicing Handler
  const handleSendInvoice = async () => {
    if (!pricingResult) return;

    setSendingInvoice(true);
    setInvoiceStatus(null);

    try {
      const res = await axios.post(`${API_BASE}/invoices/send`, {
        recipient_email: invoiceEmail,
        item_name: invoiceItem,
        amount: pricingResult.suggested_price,
        due_date: new Date(
          Date.now() + 7 * 24 * 60 * 60 * 1000
        )
          .toISOString()
          .split("T")[0],
      });

      setInvoiceStatus({
        success: true,
        id: res.data.invoice_id,
      });

      fetchSummary();
    } catch (err) {
      setInvoiceStatus({
        success: false,
        message: err.response?.data?.detail || err.message,
      });
    } finally {
      setSendingInvoice(false);
    }
  };

  // Gemini AI Chat Handler
  const handleChat = async () => {
    if (!chatPrompt.trim()) return;

    setChatLoading(true);
    setChatReply("");

    try {
      const res = await axios.post(`${API_BASE}/assistant/chat`, {
        query: chatPrompt,
      });

      setChatReply(res.data.reply);
    } catch (err) {
      setChatReply(
        err.response?.data?.detail ||
          "Unable to reach the AI assistant. Please try again."
      );
    } finally {
      setChatLoading(false);
    }
  };

  // Chart Configuration
  const forecastData = summary
    ? delayScenario
      ? summary.forecast_delayed
      : summary.forecast_normal
    : [];

  const chartData = {
    labels: forecastData.map((d) => d.date.slice(5)),

    datasets: [
      {
        label: delayScenario
          ? "Projected Balance (14-Day Payment Delay)"
          : "Projected Balance (Normal)",

        data: forecastData.map((d) => d.projected_balance),

        borderColor: delayScenario
          ? "rgba(220, 53, 69, 1)"
          : "rgba(25, 135, 84, 1)",

        backgroundColor: delayScenario
          ? "rgba(220, 53, 69, 0.1)"
          : "rgba(25, 135, 84, 0.1)",

        fill: true,
        tension: 0.3,
      },
    ],
  };

  return (
    <Container fluid className="p-4 bg-light min-vh-100">
      {/* Header */}
      <div className="d-flex justify-content-between align-items-center mb-4 pb-2 border-bottom">
        <div>
          <h2 className="fw-bold mb-0 text-primary">AuraFin</h2>

          <small className="text-muted">
            AI-Powered Financial Operating System for Independent Creators
          </small>
        </div>

        <Badge bg="dark" className="p-2">
          PayPal Invoicing + Gemini AI
        </Badge>
      </div>

      {/* KPI Cards */}
      <Row className="mb-4 g-3">
        <Col md={3}>
          <Card className="shadow-sm border-0">
            <Card.Body>
              <h6 className="text-muted text-uppercase small">
                Liquid Cash Balance
              </h6>

              <h3 className="fw-bold text-success">
                $
                {summary?.current_cash_balance?.toFixed(2) || "0.00"}
              </h3>
            </Card.Body>
          </Card>
        </Col>

        <Col md={3}>
          <Card className="shadow-sm border-0">
            <Card.Body>
              <h6 className="text-muted text-uppercase small">
                Confirmed Expenses
              </h6>

              <h3 className="fw-bold text-danger">
                ${summary?.total_expenses?.toFixed(2) || "0.00"}
              </h3>
            </Card.Body>
          </Card>
        </Col>

        <Col md={3}>
          <Card className="shadow-sm border-0">
            <Card.Body>
              <h6 className="text-muted text-uppercase small">
                Pending Invoices
              </h6>

              <h3 className="fw-bold text-warning">
                ${summary?.pending_invoices_total?.toFixed(2) || "0.00"}
              </h3>
            </Card.Body>
          </Card>
        </Col>

        <Col md={3}>
          <Card className="shadow-sm border-0">
            <Card.Body>
              <h6 className="text-muted text-uppercase small">
                PayPal Status
              </h6>

              <Badge bg="success" className="mt-2">
                Sandbox Connected
              </Badge>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Cash Flow Forecast */}
      <Row className="mb-4">
        <Col xs={12}>
          <Card className="shadow-sm border-0">
            <Card.Body>
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h5 className="fw-bold mb-0">
                  30-Day Cash-Flow Runway Forecast
                </h5>

                <Form.Check
                  type="switch"
                  id="delay-switch"
                  label="Simulate 14-Day Client Payment Delay"
                  checked={delayScenario}
                  onChange={(e) => setDelayScenario(e.target.checked)}
                />
              </div>

              <div style={{ height: "280px" }}>
                {summary && (
                  <Line
                    data={chartData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                    }}
                  />
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Pricing Advisor & Gemini AI Copilot */}
      <Row className="g-4">
        {/* Left Column: Pricing Advisor & PayPal Invoicing */}
        <Col lg={6}>
          <Card className="shadow-sm border-0 h-100">
            <Card.Header className="bg-white fw-bold">
              AI Pricing Advisor & PayPal Invoicing
            </Card.Header>

            <Card.Body>
              <Row className="g-2 mb-3">
                <Col sm={6}>
                  <Form.Label className="small fw-semibold">
                    Materials Cost ($)
                  </Form.Label>

                  <Form.Control
                    type="number"
                    value={pricingInputs.materials}
                    onChange={(e) =>
                      setPricingInputs({
                        ...pricingInputs,
                        materials: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </Col>

                <Col sm={6}>
                  <Form.Label className="small fw-semibold">
                    Labor Time (Hours)
                  </Form.Label>

                  <Form.Control
                    type="number"
                    value={pricingInputs.hours}
                    onChange={(e) =>
                      setPricingInputs({
                        ...pricingInputs,
                        hours: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </Col>

                <Col sm={6}>
                  <Form.Label className="small fw-semibold">
                    Hourly Rate ($)
                  </Form.Label>

                  <Form.Control
                    type="number"
                    value={pricingInputs.rate}
                    onChange={(e) =>
                      setPricingInputs({
                        ...pricingInputs,
                        rate: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </Col>

                <Col sm={6}>
                  <Form.Label className="small fw-semibold">
                    Packaging & Shipping ($)
                  </Form.Label>

                  <Form.Control
                    type="number"
                    value={
                      pricingInputs.packaging + pricingInputs.shipping
                    }
                    onChange={(e) => {
                      const val = parseFloat(e.target.value) || 0;

                      setPricingInputs({
                        ...pricingInputs,
                        packaging: val / 2,
                        shipping: val / 2,
                      });
                    }}
                  />
                </Col>

                <Col sm={6}>
                  <Form.Label className="small fw-semibold">
                    Target Margin (%)
                  </Form.Label>

                  <Form.Control
                    type="number"
                    value={pricingInputs.target_margin}
                    onChange={(e) =>
                      setPricingInputs({
                        ...pricingInputs,
                        target_margin: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </Col>

                <Col sm={6} className="d-flex align-items-end">
                  <Button
                    variant="outline-primary"
                    className="w-100"
                    onClick={handleCalculatePrice}
                  >
                    Recalculate
                  </Button>
                </Col>
              </Row>

              {/* Pricing Result */}
              {pricingResult && (
                <div className="p-3 bg-light rounded mb-3 border">
                  <div className="d-flex justify-content-between">
                    <span>Base Production Cost:</span>
                    <strong>${pricingResult.base_cost}</strong>
                  </div>

                  <div className="d-flex justify-content-between text-success">
                    <span>Estimated Net Profit:</span>
                    <strong>
                      ${pricingResult.estimated_net_profit}
                    </strong>
                  </div>

                  <hr className="my-2" />

                  <div className="d-flex justify-content-between align-items-center">
                    <span className="fw-bold">
                      Recommended Price (Net of Fees):
                    </span>

                    <h4 className="fw-bold text-primary mb-0">
                      ${pricingResult.suggested_price}
                    </h4>
                  </div>
                </div>
              )}

              {/* PayPal Invoice Action */}
              <h6 className="fw-bold mt-4 mb-2">
                Send as Official PayPal Invoice
              </h6>

              <Form.Group className="mb-2">
                <Form.Control
                  size="sm"
                  type="email"
                  placeholder="Client PayPal Email"
                  value={invoiceEmail}
                  onChange={(e) => setInvoiceEmail(e.target.value)}
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Control
                  size="sm"
                  type="text"
                  placeholder="Line Item Description"
                  value={invoiceItem}
                  onChange={(e) => setInvoiceItem(e.target.value)}
                />
              </Form.Group>

              <Button
                variant="primary"
                className="w-100"
                onClick={handleSendInvoice}
                disabled={sendingInvoice || !pricingResult}
              >
                {sendingInvoice ? (
                  <Spinner size="sm" animation="border" />
                ) : (
                  `Create & Send Invoice ($${pricingResult?.suggested_price || 0})`
                )}
              </Button>

              {invoiceStatus && (
                <Alert
                  variant={invoiceStatus.success ? "success" : "danger"}
                  className="mt-3 py-2 small"
                >
                  {invoiceStatus.success
                    ? `Invoice dispatched! PayPal Invoice ID: ${invoiceStatus.id}`
                    : `Dispatch Failed: ${invoiceStatus.message}`}
                </Alert>
              )}
            </Card.Body>
          </Card>
        </Col>

        {/* Right Column: Gemini AI Copilot */}
        <Col lg={6}>
          <Card className="shadow-sm border-0 h-100">
            <Card.Header className="bg-white fw-bold d-flex justify-content-between align-items-center">
              <span>AI Financial Copilot</span>

              <Badge bg="success">Gemini-powered</Badge>
            </Card.Header>

            <Card.Body className="d-flex flex-column justify-content-between">
              <div>
                <p className="text-muted small">
                  Ask realistic financial questions grounded directly in
                  your database transactions, pending PayPal invoices, and
                  projected cash runway.
                </p>

                {chatReply && (
                  <div className="p-3 bg-light rounded border mb-3">
                    <h6 className="fw-bold text-dark mb-1">
                      Copilot Analysis:
                    </h6>

                    <p className="mb-0 text-secondary">{chatReply}</p>
                  </div>
                )}
              </div>

              <div>
                <Form.Group className="mb-2">
                  <Form.Control
                    as="textarea"
                    rows={3}
                    placeholder="E.g., Can I afford an annual subscription right now?"
                    value={chatPrompt}
                    onChange={(e) => setChatPrompt(e.target.value)}
                  />
                </Form.Group>

                <Button
                  variant="dark"
                  className="w-100"
                  onClick={handleChat}
                  disabled={chatLoading || !chatPrompt.trim()}
                >
                  {chatLoading ? (
                    <Spinner size="sm" animation="border" />
                  ) : (
                    "Ask Copilot"
                  )}
                </Button>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
}