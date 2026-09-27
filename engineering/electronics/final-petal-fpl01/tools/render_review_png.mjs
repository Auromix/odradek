// SPDX-License-Identifier: CC-BY-NC-4.0
// Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
import {createRequire} from 'node:module';const require=createRequire(import.meta.url);const sharp=require(process.env.FPL_SHARP_MODULE || 'sharp');
import {fileURLToPath} from 'node:url';import path from 'node:path';
const D=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const W=2200,H=1550;const titles=[['UPPER · 130 LEDs · front',30,145],['UPPER · driver side · rear view',1120,145],['LOWER · 42 LEDs · front',30,820],['LOWER · driver side · rear view',1120,820]];
let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><rect width="100%" height="100%" fill="#f5f6f8"/><text x="35" y="57" font-family="Helvetica" font-size="38" fill="#152232">FPL-01 · Native KiCad LED petal boards</text><text x="35" y="99" font-family="Helvetica" font-size="22" fill="#46566a">6 copper layers · 0.8 mm candidate · ERC / DRC / unconnected = 0 · not fabrication release</text>`;
for(const [t,x,y] of titles)svg+=`<rect x="${x}" y="${y}" width="1050" height="650" rx="10" fill="white"/><text x="${x+20}" y="${y+38}" font-family="Helvetica" font-size="26" fill="#22354a">${t}</text>`;
svg+=`<text x="35" y="1512" font-family="Helvetica" font-size="19" fill="#57677b">Native copper and component references. Views scaled independently; rear plots mirrored for readability, physical PCB design is not mirrored.</text></svg>`;
const comps=[];for(let i=0;i<4;i++){let[k,v]=[['upper','front'],['upper','back'],['lower','front'],['lower','back']][i];let img=await sharp(path.join(D,k,'kicad','plots',`${v}-review.svg`),{density:180,limitInputPixels:false}).flatten({background:'white'}).resize({width:1010,height:555,fit:'inside'}).png().toBuffer();let meta=await sharp(img).metadata();comps.push({input:img,left:titles[i][1]+20,top:titles[i][2]+75+Math.floor((540-meta.height)/2)});}
await sharp(Buffer.from(svg)).composite(comps).png().toFile(path.join(D,'board-overview.png'));
