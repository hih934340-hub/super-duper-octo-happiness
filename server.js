const express = require('express');
const axios = require('axios');
const app = express();
const PORT = 3000;

const API_URL = 'https://gbmd5-4a69a-default-rtdb.asia-southeast1.firebasedatabase.app/taixiu_sessions.json';

// ==================== LỚP PHÂN TÍCH CẦU CHUYÊN SÂU ====================
class CauAnalyzer {
    constructor(history) {
        this.history = history;
        this.cau_phat_hien = [];
        this.cau_diem = {};
    }

    // 1. Cầu bệt (dây dài)
    phatHienCauBet() {
        const last = this.history.slice(-10);
        let doDai = 1;
        for (let i = last.length - 2; i >= 0; i--) {
            if (last[i].ket_qua === last[last.length - 1].ket_qua) doDai++;
            else break;
        }
        if (doDai >= 3) {
            this.cau_phat_hien.push({
                ten: `Bệt ${last[last.length - 1].ket_qua}`,
                doDai: doDai,
                mucDo: Math.min(doDai / 10, 1),
                huong: last[last.length - 1].ket_qua
            });
        }
    }

    // 2. Cầu 1-1 (xen kẽ hoàn hảo)
    phatHienCau11() {
        const last = this.history.slice(-10);
        let check = true;
        for (let i = 1; i < last.length; i++) {
            if (last[i].ket_qua === last[i-1].ket_qua) { check = false; break; }
        }
        if (check && last.length >= 4) {
            const doDai = last.length;
            this.cau_phat_hien.push({
                ten: 'Cầu 1-1 (xen kẽ)',
                doDai: doDai,
                mucDo: Math.min(doDai / 12, 0.95),
                huong: last[last.length - 1].ket_qua === 'Tài' ? 'Xỉu' : 'Tài'
            });
        }
    }

    // 3. Cầu 2-2 (Tài Tài Xỉu Xỉu)
    phatHienCau22() {
        const last = this.history.slice(-8);
        if (last.length < 4) return;
        let check = true;
        for (let i = 0; i < last.length - 3; i += 2) {
            if (last[i].ket_qua !== last[i+1].ket_qua) { check = false; break; }
            if (i + 2 < last.length && last[i].ket_qua === last[i+2].ket_qua) { check = false; break; }
        }
        if (check && last.length >= 4) {
            this.cau_phat_hien.push({
                ten: 'Cầu 2-2 (Tài Tài Xỉu Xỉu)',
                doDai: last.length,
                mucDo: 0.85,
                huong: last[last.length - 1].ket_qua === 'Tài' ? 'Xỉu' : 'Tài'
            });
        }
    }

    // 4. Cầu 3-2 (Tài Tài Tài Xỉu Xỉu)
    phatHienCau32() {
        const last = this.history.slice(-7);
        if (last.length < 5) return;
        const pattern1 = last.slice(0,3).every(s => s.ket_qua === 'Tài');
        const pattern2 = last.slice(3,5).every(s => s.ket_qua === 'Xỉu');
        if (pattern1 && pattern2) {
            this.cau_phat_hien.push({
                ten: 'Cầu 3-2 (Tài Tài Tài Xỉu Xỉu)',
                doDai: 5,
                mucDo: 0.75,
                huong: 'Xỉu'
            });
        }
        const pattern3 = last.slice(0,3).every(s => s.ket_qua === 'Xỉu');
        const pattern4 = last.slice(3,5).every(s => s.ket_qua === 'Tài');
        if (pattern3 && pattern4) {
            this.cau_phat_hien.push({
                ten: 'Cầu 3-2 (Xỉu Xỉu Xỉu Tài Tài)',
                doDai: 5,
                mucDo: 0.75,
                huong: 'Tài'
            });
        }
    }

    // 5. Cầu 1-2-1 (Tài Xỉu Xỉu Tài)
    phatHienCau121() {
        const last = this.history.slice(-5);
        if (last.length < 4) return;
        if (last[0].ket_qua === last[3].ket_qua && 
            last[1].ket_qua === last[2].ket_qua &&
            last[0].ket_qua !== last[1].ket_qua) {
            this.cau_phat_hien.push({
                ten: 'Cầu 1-2-1',
                doDai: 4,
                mucDo: 0.7,
                huong: last[0].ket_qua
            });
        }
    }

    // 6. Cầu 2-1-2 (Tài Tài Xỉu Tài Tài)
    phatHienCau212() {
        const last = this.history.slice(-6);
        if (last.length < 5) return;
        if (last[0].ket_qua === last[1].ket_qua &&
            last[3].ket_qua === last[4].ket_qua &&
            last[0].ket_qua !== last[2].ket_qua &&
            last[0].ket_qua === last[3].ket_qua) {
            this.cau_phat_hien.push({
                ten: 'Cầu 2-1-2',
                doDai: 5,
                mucDo: 0.8,
                huong: last[0].ket_qua
            });
        }
    }

    // 7. Cầu 3-1 (Tài Tài Tài Xỉu)
    phatHienCau31() {
        const last = this.history.slice(-5);
        if (last.length < 4) return;
        const checkTai = last.slice(0,3).every(s => s.ket_qua === 'Tài');
        const checkXiu = last.slice(0,3).every(s => s.ket_qua === 'Xỉu');
        if (checkTai && last[3].ket_qua === 'Xỉu') {
            this.cau_phat_hien.push({
                ten: 'Cầu 3-1 (Tài Tài Tài Xỉu)',
                doDai: 4,
                mucDo: 0.7,
                huong: 'Xỉu'
            });
        }
        if (checkXiu && last[3].ket_qua === 'Tài') {
            this.cau_phat_hien.push({
                ten: 'Cầu 3-1 (Xỉu Xỉu Xỉu Tài)',
                doDai: 4,
                mucDo: 0.7,
                huong: 'Tài'
            });
        }
    }

    // 8. Cầu 1-3 (Tài Xỉu Xỉu Xỉu)
    phatHienCau13() {
        const last = this.history.slice(-5);
        if (last.length < 4) return;
        if (last[0].ket_qua === 'Tài' && 
            last.slice(1,4).every(s => s.ket_qua === 'Xỉu')) {
            this.cau_phat_hien.push({
                ten: 'Cầu 1-3 (Tài Xỉu Xỉu Xỉu)',
                doDai: 4,
                mucDo: 0.7,
                huong: 'Xỉu'
            });
        }
        if (last[0].ket_qua === 'Xỉu' && 
            last.slice(1,4).every(s => s.ket_qua === 'Tài')) {
            this.cau_phat_hien.push({
                ten: 'Cầu 1-3 (Xỉu Tài Tài Tài)',
                doDai: 4,
                mucDo: 0.7,
                huong: 'Tài'
            });
        }
    }

    // 9. Cầu 4-2 (Tài Tài Tài Tài Xỉu Xỉu)
    phatHienCau42() {
        const last = this.history.slice(-7);
        if (last.length < 6) return;
        const checkTai = last.slice(0,4).every(s => s.ket_qua === 'Tài');
        const checkXiu = last.slice(4,6).every(s => s.ket_qua === 'Xỉu');
        if (checkTai && checkXiu) {
            this.cau_phat_hien.push({
                ten: 'Cầu 4-2 (Tài Tài Tài Tài Xỉu Xỉu)',
                doDai: 6,
                mucDo: 0.78,
                huong: 'Xỉu'
            });
        }
        const checkTai2 = last.slice(0,4).every(s => s.ket_qua === 'Xỉu');
        const checkXiu2 = last.slice(4,6).every(s => s.ket_qua === 'Tài');
        if (checkTai2 && checkXiu2) {
            this.cau_phat_hien.push({
                ten: 'Cầu 4-2 (Xỉu Xỉu Xỉu Xỉu Tài Tài)',
                doDai: 6,
                mucDo: 0.78,
                huong: 'Tài'
            });
        }
    }

    // 10. Cầu 2-4 (Tài Tài Xỉu Xỉu Xỉu Xỉu)
    phatHienCau24() {
        const last = this.history.slice(-7);
        if (last.length < 6) return;
        const checkTai = last.slice(0,2).every(s => s.ket_qua === 'Tài');
        const checkXiu = last.slice(2,6).every(s => s.ket_qua === 'Xỉu');
        if (checkTai && checkXiu) {
            this.cau_phat_hien.push({
                ten: 'Cầu 2-4 (Tài Tài Xỉu Xỉu Xỉu Xỉu)',
                doDai: 6,
                mucDo: 0.78,
                huong: 'Xỉu'
            });
        }
        const checkTai2 = last.slice(0,2).every(s => s.ket_qua === 'Xỉu');
        const checkXiu2 = last.slice(2,6).every(s => s.ket_qua === 'Tài');
        if (checkTai2 && checkXiu2) {
            this.cau_phat_hien.push({
                ten: 'Cầu 2-4 (Xỉu Xỉu Tài Tài Tài Tài)',
                doDai: 6,
                mucDo: 0.78,
                huong: 'Tài'
            });
        }
    }

    // 11. Cầu 5-1 (Tài Tài Tài Tài Tài Xỉu)
    phatHienCau51() {
        const last = this.history.slice(-7);
        if (last.length < 6) return;
        const checkTai = last.slice(0,5).every(s => s.ket_qua === 'Tài');
        if (checkTai && last[5].ket_qua === 'Xỉu') {
            this.cau_phat_hien.push({
                ten: 'Cầu 5-1 (Tài Tài Tài Tài Tài Xỉu)',
                doDai: 6,
                mucDo: 0.75,
                huong: 'Xỉu'
            });
        }
        const checkXiu = last.slice(0,5).every(s => s.ket_qua === 'Xỉu');
        if (checkXiu && last[5].ket_qua === 'Tài') {
            this.cau_phat_hien.push({
                ten: 'Cầu 5-1 (Xỉu Xỉu Xỉu Xỉu Xỉu Tài)',
                doDai: 6,
                mucDo: 0.75,
                huong: 'Tài'
            });
        }
    }

    // 12. Cầu 1-5 (Tài Xỉu Xỉu Xỉu Xỉu Xỉu)
    phatHienCau15() {
        const last = this.history.slice(-7);
        if (last.length < 6) return;
        if (last[0].ket_qua === 'Tài' && 
            last.slice(1,6).every(s => s.ket_qua === 'Xỉu')) {
            this.cau_phat_hien.push({
                ten: 'Cầu 1-5 (Tài Xỉu Xỉu Xỉu Xỉu Xỉu)',
                doDai: 6,
                mucDo: 0.75,
                huong: 'Xỉu'
            });
        }
        if (last[0].ket_qua === 'Xỉu' && 
            last.slice(1,6).every(s => s.ket_qua === 'Tài')) {
            this.cau_phat_hien.push({
                ten: 'Cầu 1-5 (Xỉu Tài Tài Tài Tài Tài)',
                doDai: 6,
                mucDo: 0.75,
                huong: 'Tài'
            });
        }
    }

    // Phân tích tổng hợp tất cả cầu
    phanTichTatCaCau() {
        this.phatHienCauBet();
        this.phatHienCau11();
        this.phatHienCau22();
        this.phatHienCau32();
        this.phatHienCau121();
        this.phatHienCau212();
        this.phatHienCau31();
        this.phatHienCau13();
        this.phatHienCau42();
        this.phatHienCau24();
        this.phatHienCau51();
        this.phatHienCau15();

        // Sắp xếp cầu theo độ mạnh
        this.cau_phat_hien.sort((a, b) => b.mucDo - a.mucDo);
        return this.cau_phat_hien;
    }

    // Lấy cầu mạnh nhất
    layCauManhNhat() {
        if (this.cau_phat_hien.length === 0) return null;
        return this.cau_phat_hien[0];
    }

    // Dự đoán theo cầu
    duDoanTheoCau() {
        const cauManh = this.layCauManhNhat();
        if (!cauManh) return null;
        return {
            huong: cauManh.huong,
            doTinCay: cauManh.mucDo,
            tenCau: cauManh.ten,
            doDai: cauManh.doDai
        };
    }
}

// ==================== LỚP PHÂN TÍCH XÁC SUẤT NÂNG CAO ====================
class XacSuatAnalyzer {
    constructor(history) {
        this.history = history;
        this.recent20 = history.slice(-20);
        this.recent50 = history.slice(-50);
    }

    // Phân tích tỷ lệ Tài/Xỉu tổng thể
    phanTichTyLe() {
        const total = this.recent50.length;
        const tai = this.recent50.filter(s => s.ket_qua === 'Tài').length;
        const xiu = total - tai;
        const tyLeTai = tai / total;
        
        return {
            tyLeTai: tyLeTai,
            tyLeXiu: 1 - tyLeTai,
            chenhLech: Math.abs(tai - xiu),
            taiCount: tai,
            xiuCount: xiu
        };
    }

    // Phân tích xu hướng với trọng số
    phanTichXuHuong() {
        const weights = [1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1];
        let score = 0;
        let totalWeight = 0;
        
        for (let i = 0; i < Math.min(10, this.recent20.length); i++) {
            const idx = this.recent20.length - 1 - i;
            if (idx < 0) break;
            const w = weights[i] || 0;
            score += (this.recent20[idx].ket_qua === 'Tài' ? 1 : -1) * w;
            totalWeight += w;
        }
        
        const diemChuan = score / totalWeight;
        return {
            diemXuHuong: diemChuan,
            huong: diemChuan > 0 ? 'Tài' : 'Xỉu',
            mucDo: Math.min(Math.abs(diemChuan), 1)
        };
    }

    // Phân tích tổng điểm
    phanTichTongDiem() {
        const tong = this.recent50.map(s => s.tong);
        const avg = tong.reduce((a, b) => a + b, 0) / tong.length;
        const max = Math.max(...tong);
        const min = Math.min(...tong);
        
        // Phân tích khoảng
        const taiCount = tong.filter(t => t >= 11).length;
        const xiuCount = tong.filter(t => t <= 10).length;
        const tileTai = taiCount / tong.length;
        
        // Phân tích tổng ở các khoảng
        const khoang = { '3-6': 0, '7-10': 0, '11-14': 0, '15-18': 0 };
        tong.forEach(t => {
            if (t <= 6) khoang['3-6']++;
            else if (t <= 10) khoang['7-10']++;
            else if (t <= 14) khoang['11-14']++;
            else khoang['15-18']++;
        });
        
        return {
            trungBinh: avg,
            max: max,
            min: min,
            tileTai: tileTai,
            khoang: khoang,
            tongGanDay: tong.slice(-5)
        };
    }

    // Phân tích mặt xúc xắc chi tiết
    phanTichMatXucXac() {
        const mat = {1:0, 2:0, 3:0, 4:0, 5:0, 6:0};
        const ganDay = {1:0, 2:0, 3:0, 4:0, 5:0, 6:0};
        const last10 = this.recent20.slice(-10);
        
        this.recent50.forEach(s => {
            mat[s.x1]++; mat[s.x2]++; mat[s.x3]++;
        });
        
        last10.forEach(s => {
            ganDay[s.x1]++; ganDay[s.x2]++; ganDay[s.x3]++;
        });
        
        const total = this.recent50.length * 3;
        const tyLe = {};
        const tyLeGanDay = {};
        let sum = 0;
        let sumGanDay = 0;
        
        Object.keys(mat).forEach(k => {
            tyLe[k] = mat[k] / total;
            tyLeGanDay[k] = ganDay[k] / (last10.length * 3);
            sum += mat[k] * parseInt(k);
            sumGanDay += ganDay[k] * parseInt(k);
        });
        
        const avgMat = sum / total;
        const avgMatGanDay = sumGanDay / (last10.length * 3);
        
        return {
            tyLe: tyLe,
            tyLeGanDay: tyLeGanDay,
            trungBinh: avgMat,
            trungBinhGanDay: avgMatGanDay,
            matXuatHienNhieu: Object.keys(tyLe).reduce((a, b) => tyLe[a] > tyLe[b] ? a : b),
            matXuatHienIt: Object.keys(tyLe).reduce((a, b) => tyLe[a] < tyLe[b] ? a : b)
        };
    }

    // Phân tích mô hình Markov bậc 1
    phanTichMarkov() {
        const markov = {};
        const states = ['Tài', 'Xỉu'];
        states.forEach(s1 => {
            markov[s1] = {};
            states.forEach(s2 => markov[s1][s2] = 0);
        });
        
        for (let i = 0; i < this.recent50.length - 1; i++) {
            const from = this.recent50[i].ket_qua;
            const to = this.recent50[i+1].ket_qua;
            markov[from][to]++;
        }
        
        // Chuyển thành xác suất
        states.forEach(s1 => {
            const total = Object.values(markov[s1]).reduce((a, b) => a + b, 0);
            if (total > 0) {
                states.forEach(s2 => markov[s1][s2] /= total);
            }
        });
        
        const lastState = this.recent50[this.recent50.length - 1].ket_qua;
        const probTai = markov[lastState]?.['Tài'] || 0.5;
        const probXiu = markov[lastState]?.['Xỉu'] || 0.5;
        
        return {
            maTran: markov,
            lastState: lastState,
            probTai: probTai,
            probXiu: probXiu,
            ketLuan: probTai > probXiu ? 'Tài' : 'Xỉu'
        };
    }

    // Phân tích chu kỳ
    phanTichChuKy() {
        const results = [];
        for (let k = 2; k <= 10; k++) {
            let match = 0;
            for (let i = 0; i < this.recent50.length - k; i++) {
                if (this.recent50[i].ket_qua === this.recent50[i+k].ket_qua) match++;
            }
            const tyLe = match / (this.recent50.length - k);
            results.push({ chuKy: k, tyLe: tyLe });
        }
        return results;
    }

    // Phân tích đột biến
    phanTichDotBien() {
        const last5 = this.recent50.slice(-5);
        const dotBien = [];
        
        for (let i = 1; i < last5.length; i++) {
            if (last5[i].ket_qua !== last5[i-1].ket_qua) {
                dotBien.push({
                    viTri: i,
                    tu: last5[i-1].ket_qua,
                    den: last5[i].ket_qua
                });
            }
        }
        
        const tanSoDotBien = dotBien.length / (last5.length - 1);
        return {
            dotBien: dotBien,
            tanSo: tanSoDotBien,
            doBienDong: Math.min(tanSoDotBien * 2, 1)
        };
    }
}

// ==================== LỚP TỔNG HỢP QUYẾT ĐỊNH ====================
class DecisionMaker {
    constructor(history) {
        this.history = history;
        this.cauAnalyzer = new CauAnalyzer(history);
        this.xacSuatAnalyzer = new XacSuatAnalyzer(history);
    }

    // Tổng hợp tất cả phân tích
    tongHopPhanTich() {
        // 1. Phân tích cầu
        const cauPhatHien = this.cauAnalyzer.phanTichTatCaCau();
        const duDoanCau = this.cauAnalyzer.duDoanTheoCau();
        
        // 2. Phân tích xác suất
        const tyLe = this.xacSuatAnalyzer.phanTichTyLe();
        const xuHuong = this.xacSuatAnalyzer.phanTichXuHuong();
        const tongDiem = this.xacSuatAnalyzer.phanTichTongDiem();
        const matXucXac = this.xacSuatAnalyzer.phanTichMatXucXac();
        const markov = this.xacSuatAnalyzer.phanTichMarkov();
        const chuKy = this.xacSuatAnalyzer.phanTichChuKy();
        const dotBien = this.xacSuatAnalyzer.phanTichDotBien();
        
        // 3. Tính điểm tổng hợp (không thiên vị)
        let diemTai = 0;
        let trongSo = {
            tyLe: 0.20,
            xuHuong: 0.15,
            tongDiem: 0.15,
            matXucXac: 0.10,
            markov: 0.15,
            cau: 0.20,
            dotBien: 0.05
        };
        
        // Điểm từ tỷ lệ
        const diemTyLe = (tyLe.tyLeTai - 0.5) * 2;
        diemTai += diemTyLe * trongSo.tyLe;
        
        // Điểm từ xu hướng
        const diemXuHuong = xuHuong.diemXuHuong;
        diemTai += diemXuHuong * trongSo.xuHuong;
        
        // Điểm từ tổng điểm
        const diemTong = (tongDiem.tileTai - 0.5) * 2;
        diemTai += diemTong * trongSo.tongDiem;
        
        // Điểm từ mặt xúc xắc
        const diemMat = (matXucXac.trungBinhGanDay - 3.5) / 2.5;
        diemTai += diemMat * trongSo.matXucXac;
        
        // Điểm từ Markov
        const diemMarkov = (markov.probTai - 0.5) * 2;
        diemTai += diemMarkov * trongSo.markov;
        
        // Điểm từ cầu
        if (duDoanCau) {
            const diemCau = duDoanCau.huong === 'Tài' ? 1 : -1;
            diemTai += diemCau * duDoanCau.doTinCay * trongSo.cau;
        }
        
        // Điều chỉnh đột biến
        if (dotBien.tanSo > 0.5) {
            diemTai *= (1 - dotBien.doBienDong * 0.3);
        }
        
        // Quyết định cuối cùng
        const threshold = 0.05;
        let ketQua = '';
        let doTinCay = 0;
        let diemSo = diemTai;
        
        if (Math.abs(diemSo) < threshold) {
            ketQua = 'Cân bằng';
            doTinCay = 0.5;
        } else if (diemSo > 0) {
            ketQua = 'Tài';
            doTinCay = Math.min(0.5 + diemSo * 2, 0.95);
        } else {
            ketQua = 'Xỉu';
            doTinCay = Math.min(0.5 + Math.abs(diemSo) * 2, 0.95);
        }
        
        // Lấy cầu mạnh nhất làm cầu chính
        const cauChinh = cauPhatHien.length > 0 ? cauPhatHien[0] : null;
        
        return {
            duDoan: ketQua,
            doTinCay: doTinCay,
            diemTai: diemSo,
            cauChinh: cauChinh,
            tatCaCau: cauPhatHien.slice(0, 5),
            phanTichChiTiet: {
                tyLe: tyLe,
                xuHuong: xuHuong,
                tongDiem: tongDiem,
                matXucXac: matXucXac,
                markov: markov,
                dotBien: dotBien,
                chuKy: chuKy.slice(0, 3)
            }
        };
    }
}

// ==================== SERVER EXPRESS ====================
async function fetchHistory() {
    const response = await axios.get(API_URL);
    const data = response.data;
    
    const sessions = Object.keys(data)
        .filter(key => key.includes('_end'))
        .map(key => {
            const session = data[key];
            return {
                id: session.phien,
                tong: session.tong,
                ket_qua: session.ket_qua,
                x1: session.xuc_xac_1,
                x2: session.xuc_xac_2,
                x3: session.xuc_xac_3,
                time: new Date(session.time)
            };
        })
        .sort((a, b) => a.time - b.time);
    
    return sessions;
}

app.get('/api/predict', async (req, res) => {
    try {
        const history = await fetchHistory();
        
        if (history.length < 15) {
            return res.json({
                phien_truoc: history.length > 0 ? {
                    id: history[history.length-1].id,
                    tong: history[history.length-1].tong,
                    ket_qua: history[history.length-1].ket_qua
                } : null,
                phien_du_doan: 'Chờ dữ liệu',
                du_doan: 'Chưa đủ',
                ti_le: '0%',
                cau_phat_hien: [],
                phan_tich: null,
                id: '@tranhoang2286'
            });
        }
        
        const maker = new DecisionMaker(history);
        const result = maker.tongHopPhanTich();
        
        const lastSession = history[history.length - 1];
        const nextId = String(Number(lastSession.id) + 1);
        
        // Format cầu để hiển thị
        const cauDisplay = result.tatCaCau.map(c => 
            `${c.ten} (độ dài: ${c.doDai}, tin cậy: ${(c.mucDo * 100).toFixed(0)}%)`
        );
        
        res.json({
            phien_truoc: {
                id: lastSession.id,
                tong: lastSession.tong,
                ket_qua: lastSession.ket_qua,
                xuc_xac: `${lastSession.x1}-${lastSession.x2}-${lastSession.x3}`
            },
            phien_du_doan: nextId,
            du_doan: result.duDoan,
            ti_le: (result.doTinCay * 100).toFixed(0) + '%',
            cau_chinh: result.cauChinh ? {
                ten: result.cauChinh.ten,
                do_dai: result.cauChinh.doDai,
                muc_do: (result.cauChinh.mucDo * 100).toFixed(0) + '%',
                huong_du_doan: result.cauChinh.huong
            } : 'Không phát hiện cầu rõ ràng',
            tat_ca_cau: cauDisplay,
            phan_tich_chi_tiet: {
                ty_le_tai: (result.phanTichChiTiet.tyLe.tyLeTai * 100).toFixed(1) + '%',
                xu_huong: result.phanTichChiTiet.xuHuong.huong,
                do_xu_huong: (result.phanTichChiTiet.xuHuong.mucDo * 100).toFixed(0) + '%',
                tong_trung_binh: result.phanTichChiTiet.tongDiem.trungBinh.toFixed(2),
                mat_trung_binh: result.phanTichChiTiet.matXucXac.trungBinhGanDay.toFixed(2),
                mat_xuat_hien_nhieu: result.phanTichChiTiet.matXucXac.matXuatHienNhieu,
                do_bien_dong: (result.phanTichChiTiet.dotBien.doBienDong * 100).toFixed(0) + '%',
                markov: result.phanTichChiTiet.markov.ketLuan
            },
            id: '@tranhoang2286'
        });
        
    } catch (error) {
        res.status(500).json({
            error: 'Lỗi phân tích',
            message: error.message,
            id: '@tranhoang2286'
        });
    }
});

app.get('/api/history', async (req, res) => {
    try {
        const history = await fetchHistory();
        const last30 = history.slice(-30).map(s => ({
            phien: s.id,
            tong: s.tong,
            ket_qua: s.ket_qua,
            xuc_xac: `${s.x1}-${s.x2}-${s.x3}`
        }));
        res.json({
            tong_so_phien: history.length,
            ket_qua_gan_day: last30,
            thong_ke_nhanh: {
                tai: history.filter(s => s.ket_qua === 'Tài').length,
                xiu: history.filter(s => s.ket_qua === 'Xỉu').length,
                ti_le_tai: ((history.filter(s => s.ket_qua === 'Tài').length / history.length) * 100).toFixed(1) + '%'
            },
            id: '@tranhoang2286'
        });
    } catch (error) {
        res.status(500).json({
            error: 'Lỗi lấy lịch sử',
            message: error.message,
            id: '@tranhoang2286'
        });
    }
});

app.get('/api/cau', async (req, res) => {
    try {
        const history = await fetchHistory();
        const maker = new DecisionMaker(history);
        const cau = maker.cauAnalyzer.phanTichTatCaCau();
        res.json({
            cau_phat_hien: cau.map(c => ({
                ten: c.ten,
                do_dai: c.doDai,
                muc_do: (c.mucDo * 100).toFixed(0) + '%',
                huong_du_doan: c.huong
            })),
            so_luong_cau: cau.length,
            id: '@tranhoang2286'
        });
    } catch (error) {
        res.status(500).json({
            error: 'Lỗi phân tích cầu',
            message: error.message,
            id: '@tranhoang2286'
        });
    }
});

app.listen(PORT, () => {
    console.log('╔═══════════════════════════════════════════╗');
    console.log('║   🎲  TÀI XỈU PREDICTOR V4.0  🎲        ║');
    console.log('║   Thuật toán nhận diện 12 loại cầu      ║');
    console.log('║   Phân tích đa chiều không thiên vị     ║');
    console.log('╚═══════════════════════════════════════════╝');
    console.log(`🚀 Server: http://localhost:${PORT}`);
    console.log(`📊 Dự đoán: http://localhost:${PORT}/api/predict`);
    console.log(`📜 Lịch sử: http://localhost:${PORT}/api/history`);
    console.log(`🎯 Phân tích cầu: http://localhost:${PORT}/api/cau`);
    console.log(`👤 ID: @tranhoang2286`);
});
