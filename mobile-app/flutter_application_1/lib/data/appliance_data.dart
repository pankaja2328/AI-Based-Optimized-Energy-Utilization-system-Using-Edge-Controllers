// lib/data/appliance_data.dart
import '../models/appliance.dart';

List<Appliance> appliances = [
  Appliance(
    name: 'TV',
    onHours: '1600h - 1800h',
    offHours: '1800h - 1600h',
    prediction: [1.2, 1.3, 1.5, 1.4, 1.6],
    usage: "1.6 kWh",
    cost: "LKR 60",
    savings: "LKR 12",
  ),
  Appliance(
    name: 'AC',
    onHours: '1600h - 1800h',
    offHours: '1800h - 1600h',
    prediction: [2.0, 2.5, 2.2, 2.8, 3.0],
    usage: "3.0 kWh",
    cost: "LKR 120",
    savings: "LKR 30",
  ),
  Appliance(
    name: 'Lampara',
    onHours: '1600h - 1800h',
    offHours: '1800h - 1600h',
    prediction: [0.5, 0.6, 0.7, 0.5, 0.6],
    usage: "0.6 kWh",
    cost: "LKR 20",
    savings: "LKR 5",
  ),
  Appliance(
    name: 'Ventilador',
    onHours: '1600h - 1800h',
    offHours: '1800h - 1600h',
    prediction: [0.8, 0.9, 1.0, 1.1, 1.0],
    usage: "1.0 kWh",
    cost: "LKR 40",
    savings: "LKR 8",
  ),
  Appliance(
    name: 'PC',
    onHours: '1600h - 1800h',
    offHours: '1800h - 1600h',
    prediction: [1.5, 1.7, 1.8, 2.0, 2.1],
    usage: "2.1 kWh",
    cost: "LKR 85",
    savings: "LKR 15",
  ),
];
